#requires -Version 5.1
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# Move to project root (parent of this script directory)
$Root = Resolve-Path (Join-Path $PSScriptRoot '..')
Set-Location $Root

# Optionally activate virtual environment if available
$VenvActivate = Join-Path $Root '.venv\Scripts\Activate.ps1'
if (Test-Path $VenvActivate) {
    try { . $VenvActivate } catch { }
}

# Read backend/.env for default DJANGO_SUPERUSER_* if present
function Read-DotEnv {
  param([string]$Path)
  $result = @{}
  if (-not (Test-Path -Path $Path)) { return $result }
  try {
    Get-Content $Path | Where-Object { $_ -and ($_ -notmatch '^\s*#') } | ForEach-Object {
      if ($_ -match '^(?<k>[^=\s]+)=(?<v>.*)$') { $result[$Matches['k'].Trim()] = $Matches['v'].Trim() }
    }
  } catch { }
  return $result
}

function ConvertFrom-QuotedValue {
  param([string]$s)
  if (-not $s) { return $s }
  $t = $s.Trim()
  if ($t.Length -ge 2) {
    $f = $t[0]; $l = $t[$t.Length-1]
    if (($f -eq '"' -and $l -eq '"') -or ($f -eq "'" -and $l -eq "'")) { return $t.Substring(1, $t.Length-2) }
  }
  return $t
}

function Test-DjangoDbConnection {
  try {
    $BackendPath = Join-Path $Root 'backend'
    $BackendPathEsc = ($BackendPath -replace '\\','\\')
    $code = @"
import os, sys
p = r'$BackendPathEsc'
if p not in sys.path: sys.path.insert(0, p)
os.environ.setdefault('DJANGO_SETTINGS_MODULE','core.settings')
try:
    import django
    django.setup()
    from django.db import connection
    with connection.cursor() as c:
        c.execute('SELECT 1')
        c.fetchone()
    print('OK')
    raise SystemExit(0)
except Exception:
    raise SystemExit(1)
"@
    $tmp = New-TemporaryFile
    Set-Content -Path $tmp -Value $code -Encoding UTF8
    $out = & python $tmp 2>$null
    $exit = $LASTEXITCODE
    Remove-Item $tmp -ErrorAction SilentlyContinue
    return ($exit -eq 0 -and ($out -match 'OK'))
  } catch { return $false }
}

function Get-DjangoDbErrorSummary {
  try {
    $BackendPath = Join-Path $Root 'backend'
    $BackendPathEsc = ($BackendPath -replace '\\','\\')
    $code = @"
import os, sys, json
p = r'$BackendPathEsc'
if p not in sys.path: sys.path.insert(0, p)
os.environ.setdefault('DJANGO_SETTINGS_MODULE','core.settings')
try:
    import django
    django.setup()
    from django.conf import settings
    from django.db import connection
    db = settings.DATABASES.get('default', {})
    db_print = dict(db)
    if 'PASSWORD' in db_print and db_print['PASSWORD']:
        db_print['PASSWORD'] = '(set)'
    print('DJANGO_DB=', json.dumps(db_print, ensure_ascii=False))
    with connection.cursor() as c:
        c.execute('SELECT 1')
        c.fetchone()
    print('OK')
    raise SystemExit(0)
except Exception as e:
    et = type(e)
    print(f"{et.__module__}.{et.__name__}: {e}")
    raise SystemExit(1)
"@
    $tmp = New-TemporaryFile
    Set-Content -Path $tmp -Value $code -Encoding UTF8
    $output = & python $tmp 2>&1
    $exit = $LASTEXITCODE
    Remove-Item $tmp -ErrorAction SilentlyContinue
    if ($exit -eq 0) { return $null }
    foreach ($line in ($output -split "`r?`n")) { if ($line.Trim()) { return $line.Trim() } }
    return $null
  } catch { return $null }
}

function Ensure-DbReady {
  param([hashtable]$DotEnv)
  $ready = $false
  try {
    # Export DATABASE_URL from PG_* (preferred) or DB_* values
    if (-not $Env:DATABASE_URL -or $Env:DATABASE_URL.Trim() -eq '') {
      $pgHost = if ($DotEnv['PG_HOST']) { $DotEnv['PG_HOST'] } elseif ($DotEnv['DB_HOST']) { $DotEnv['DB_HOST'] } else { $null }
      $pgPort = if ($DotEnv['PG_PORT']) { $DotEnv['PG_PORT'] } elseif ($DotEnv['DB_PORT']) { $DotEnv['DB_PORT'] } else { $null }
      $pgDb   = if ($DotEnv['PG_DB'])   { $DotEnv['PG_DB']   } elseif ($DotEnv['DB_NAME']) { $DotEnv['DB_NAME'] } else { $null }
      $pgUser = if ($DotEnv['PG_USER']) { $DotEnv['PG_USER'] } elseif ($DotEnv['DB_USER']) { $DotEnv['DB_USER'] } else { $null }
      $pgPass = if ($DotEnv['PG_PASSWORD']) { $DotEnv['PG_PASSWORD'] } elseif ($DotEnv['DB_PASSWORD']) { $DotEnv['DB_PASSWORD'] } else { $null }
      $h = ConvertFrom-QuotedValue $pgHost; if (-not $h -or $h -eq '') { $h = '127.0.0.1' }
      $p = ConvertFrom-QuotedValue $pgPort; if (-not $p -or $p -eq '') { $p = '5432' } else { $p = ($p -replace '[^\d]','') }; if (-not $p) { $p = '5432' }
      $d = ConvertFrom-QuotedValue $pgDb;   if (-not $d -or $d -eq '') { $d = 'sh_school' }
      $u = ConvertFrom-QuotedValue $pgUser; if (-not $u -or $u -eq '') { $u = 'postgres' }
      $w = ConvertFrom-QuotedValue $pgPass; if (-not $w -or $w -eq '') { $w = 'postgres' }
      $Env:DATABASE_URL = ("postgresql://{0}:{1}@{2}:{3}/{4}" -f $u, $w, $h, $p, $d)
      try { Remove-Item Env:DJANGO_DEV_SQLITE -ErrorAction SilentlyContinue } catch {}
    }
  } catch { Write-Host ("[ensure_superuser] Warning: failed to export DATABASE_URL: {0}" -f $_.Exception.Message) -ForegroundColor DarkYellow }

  # Quick success path
  if (Test-DjangoDbConnection) { return $true }

  # Probe and self-heal using db_up.ps1, with retries
  $summary = Get-DjangoDbErrorSummary
  Write-Warning "Database connection check failed. Attempting to start/align local PostgreSQL (Docker) ..."
  try { & (Join-Path $Root 'scripts\db_up.ps1') } catch { Write-Host ("[ensure_superuser] db_up.ps1 failed: {0}" -f $_.Exception.Message) -ForegroundColor DarkGray }
  # Retry a few times to allow service readiness
  for ($i=0; $i -lt 5; $i++) { if (Test-DjangoDbConnection) { return $true }; Start-Sleep -Seconds 1 }

  # If still not ready and error hints at auth mismatch, force reinit once and retry
  if ($summary -and ($summary -match 'password authentication failed' -or $summary -match 'FATAL')) {
    Write-Warning "Detected probable password mismatch. Reinitializing Postgres volume (one-time) ..."
    try { & (Join-Path $Root 'scripts\db_up.ps1') -ForceReinit } catch { Write-Host ("[ensure_superuser] db_up.ps1 -ForceReinit failed: {0}" -f $_.Exception.Message) -ForegroundColor DarkGray }
    for ($j=0; $j -lt 5; $j++) { if (Test-DjangoDbConnection) { return $true }; Start-Sleep -Seconds 1 }
  }

  # Final failure
  $final = Get-DjangoDbErrorSummary
  if ($final) { Write-Host ("Backend DB error: {0}" -f $final) -ForegroundColor DarkGray }
  return $false
}

$EnvFile = Join-Path $Root 'backend\.env'
$DotEnv = Read-DotEnv -Path $EnvFile

# Detect whether a --username was passed explicitly
$explicitUsername = $false
foreach ($a in $args) {
  if ($a -like '--username*') { $explicitUsername = $true; break }
}

# Ensure DB is ready/aligned before calling Django
$DbOk = Ensure-DbReady -DotEnv $DotEnv
if (-not $DbOk) {
  Write-Error "Database connectivity could not be established after self-heal attempts. Aborting ensure_superuser to avoid misleading stack traces. Try: pwsh -File scripts/db_up.ps1 -ForceReinit or check docker logs pg-sh-school"
  exit 1
}

# If username not provided via args, supply sensible defaults from .env or fallback
if (-not $explicitUsername) {
  $su = if ($DotEnv['DJANGO_SUPERUSER_USERNAME']) { $DotEnv['DJANGO_SUPERUSER_USERNAME'] } else { 'mesuef' }
  if ($DotEnv['DJANGO_SUPERUSER_EMAIL'])    { $env:DJANGO_SUPERUSER_EMAIL    = $DotEnv['DJANGO_SUPERUSER_EMAIL'] }
  if ($DotEnv['DJANGO_SUPERUSER_PASSWORD']) { $env:DJANGO_SUPERUSER_PASSWORD = $DotEnv['DJANGO_SUPERUSER_PASSWORD'] }
  $env:DJANGO_SUPERUSER_USERNAME = $su
  Write-Host ("Ensuring superuser '{0}' (from .env or default) ..." -f $su) -ForegroundColor DarkGray
  python backend\manage.py ensure_superuser --username $su
} else {
  # Pass through args as-is; still export optional email/password if available
  if ($DotEnv['DJANGO_SUPERUSER_EMAIL'])    { $env:DJANGO_SUPERUSER_EMAIL    = $DotEnv['DJANGO_SUPERUSER_EMAIL'] }
  if ($DotEnv['DJANGO_SUPERUSER_PASSWORD']) { $env:DJANGO_SUPERUSER_PASSWORD = $DotEnv['DJANGO_SUPERUSER_PASSWORD'] }
  python backend\manage.py ensure_superuser @args
}
