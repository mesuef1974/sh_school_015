#requires -Version 5.1
<#!
Professional one-step import of a PostgreSQL backup into the local dev database.

Usage examples:
  # Import a specific file
  ./scripts/import_backup.ps1 -FilePath "D:\sh_school_015\backups\pg_backup_sh_school_20251029_085528.sql"

  # Import the latest file from backups/ automatically
  ./scripts/import_backup.ps1 -Latest

This script will:
  1) Ensure the local Postgres dev container is up (scripts/db_up.ps1)
  2) Restore the backup using scripts/db_restore.ps1 (drops schema unless -SkipDrop)
  3) Run Django migrations (idempotent)
  4) Ensure the configured superuser exists (best-effort)
  5) Print a quick health/probe summary
!#>
param(
  [string]$FilePath,
  [switch]$Latest,
  [switch]$SkipDrop,
  [switch]$AssumeYes,
  [switch]$Force
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function ConvertFrom-QuotedValue {
  param([string]$s)
  if (-not $s) { return $s }
  $t = $s.Trim()
  if ($t.Length -ge 2) {
    $first = $t[0]; $last = $t[$t.Length-1]
    if (($first -eq '"' -and $last -eq '"') -or ($first -eq "'" -and $last -eq "'")) {
      return $t.Substring(1, $t.Length - 2)
    }
  }
  return $t
}

# Resolve repo root
$Root = Resolve-Path (Join-Path $PSScriptRoot '..')
Set-Location $Root

Write-Host '== Sh-School | Import PostgreSQL Backup ==' -ForegroundColor Cyan

# Ensure virtualenv
$venv = Join-Path $Root '.venv\Scripts\Activate.ps1'
if (Test-Path -LiteralPath $venv) { try { . $venv } catch { } }

# Ensure Python available
try { python --version *> $null } catch { Write-Error 'Python not found on PATH or venv not activated.'; exit 1 }

# 1) Ensure DB is up (auto-fixes common password/volume issues)
Write-Host '[import] Ensuring PostgreSQL container is up ...' -ForegroundColor DarkGray
& (Join-Path $Root 'scripts\db_up.ps1')

# Ensure Django will use the same DB credentials as the container by exporting PG_* from backend/.env
try {
  $pgEnvFile = Join-Path $Root 'backend\.env'
  $pgVars = @{}
  if (Test-Path -LiteralPath $pgEnvFile) {
    Get-Content $pgEnvFile | Where-Object { $_ -and ($_ -notmatch '^\s*#') } | ForEach-Object {
      if ($_ -match '^(?<k>[^=\s]+)=(?<v>.*)$') { $pgVars[$Matches['k'].Trim()] = $Matches['v'].Trim() }
    }
  }
  # Unquote and set defaults
  $h = ConvertFrom-QuotedValue ($pgVars['PG_HOST']); if (-not $h -or $h -eq '') { $h = '127.0.0.1' }
  $p = ConvertFrom-QuotedValue ($pgVars['PG_PORT']); if (-not $p -or $p -eq '') { $p = '5432' } else { $p = ($p -replace '[^\d]','') }
  try { $pNum = [int]$p } catch { $pNum = 5432 }
  if ($pNum -lt 1 -or $pNum -gt 65535) { $pNum = 5432 }
  $d = ConvertFrom-QuotedValue ($pgVars['PG_DB']);   if (-not $d -or $d -eq '') { $d = 'sh_school' }
  $u = ConvertFrom-QuotedValue ($pgVars['PG_USER']); if (-not $u -or $u -eq '') { $u = 'postgres' }
  $w = ConvertFrom-QuotedValue ($pgVars['PG_PASSWORD']); if (-not $w -or $w -eq '') { $w = 'postgres' }

  # Prefer runtime-selected port if present (chosen by db_up.ps1 when 5432 is busy)
  try {
    $RuntimePortFile = Join-Path $Root 'backend\.runtime\pg_port.txt'
    if (Test-Path -LiteralPath $RuntimePortFile) {
      $pRt = (Get-Content -LiteralPath $RuntimePortFile -ErrorAction SilentlyContinue | Select-Object -First 1).Trim()
      if ($pRt) { try { $pNum = [int]($pRt -replace '[^\d]','') } catch { } }
    }
  } catch { }

  $env:PG_HOST = $h
  $env:PG_PORT = [string]$pNum
  $env:PG_DB = $d
  $env:PG_USER = $u
  $env:PG_PASSWORD = $w

  # Align Django with these exact credentials as well
  $env:DATABASE_URL = ("postgresql://{0}:{1}@{2}:{3}/{4}" -f $u, $w, $h, [string]$pNum, $d)
  # Disable auto-loading backend/.env by Django to avoid accidental overrides during this script
  $env:DJANGO_READ_DOTENV = '0'

  # Enforce PostgreSQL (ensure any leftover SQLite dev flag is removed)
  try { Remove-Item Env:DJANGO_DEV_SQLITE -ErrorAction SilentlyContinue } catch {}
  Write-Host ("[import] Using PG settings: host={0} port={1} db={2} user={3}" -f $env:PG_HOST,$env:PG_PORT,$env:PG_DB,$env:PG_USER) -ForegroundColor DarkGray
} catch { Write-Host "[import] Warning: failed to export PG_* from .env: $($_.Exception.Message)" -ForegroundColor DarkYellow }

# Quick DB connectivity probe (after exporting PG_*). Fail early with clear diagnostics if credentials mismatch.
function Test-DjangoDbConnection {
  try {
    $BackendPath = Join-Path $Root 'backend'
    $BackendPathEsc = ($BackendPath -replace '\\','\\')
    $code = @"
import os, sys
backend_path = r'$BackendPathEsc'
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)
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
    $output = & python $tmp 2>$null
    $exit = $LASTEXITCODE
    Remove-Item $tmp -ErrorAction SilentlyContinue
    return ($exit -eq 0 -and ($output -match 'OK'))
  } catch { return $false }
}
function Get-DjangoDbErrorSummary {
  try {
    $BackendPath = Join-Path $Root 'backend'
    $BackendPathEsc = ($BackendPath -replace '\\','\\')
    $code = @"
import os, sys, json
backend_path = r'$BackendPathEsc'
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)
os.environ.setdefault('DJANGO_SETTINGS_MODULE','core.settings')
try:
    import django
    django.setup()
    from django.conf import settings
    from django.db import connection
    # Print resolved DB settings (masked password) to help diagnose
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

function Test-PsycopgConnection {
  try {
    $code = @"
import os
host = os.getenv('PG_HOST','127.0.0.1')
port = int(os.getenv('PG_PORT','5432'))
user = os.getenv('PG_USER','postgres')
password = os.getenv('PG_PASSWORD','postgres')
db = os.getenv('PG_DB','postgres')
try:
    import psycopg2
    conn = psycopg2.connect(host=host, port=port, user=user, password=password, dbname=db)
    cur = conn.cursor(); cur.execute('SELECT 1'); cur.fetchone(); conn.close()
    print('OK')
except Exception as e:
    print(type(e).__name__, e)
"@
    $tmp = New-TemporaryFile
    Set-Content -Path $tmp -Value $code -Encoding UTF8
    $output = & python $tmp 2>&1
    $exit = $LASTEXITCODE
    Remove-Item $tmp -ErrorAction SilentlyContinue
    return @{ exit=$exit; output=($output | Out-String) }
  } catch { return @{ exit=1; output=$_.Exception.Message } }
}

# Retry Django DB connectivity a few times to tolerate transient readiness
$ok = $false
for ($i=0; $i -lt 5; $i++) {
  if (Test-DjangoDbConnection) { $ok = $true; break }
  Start-Sleep -Seconds 1
}
if (-not $ok) {
  $summary = Get-DjangoDbErrorSummary
  $pgHost = $env:PG_HOST; if (-not $pgHost) { $pgHost = '127.0.0.1' }
  $pgPort = $env:PG_PORT; if (-not $pgPort) { $pgPort = '5432' }
  $pgDb   = $env:PG_DB;   if (-not $pgDb)   { $pgDb = 'sh_school' }
  $pgUser = $env:PG_USER; if (-not $pgUser) { $pgUser = 'postgres' }
  Write-Host "Database connectivity probe failed before restore/migrate. Ensure credentials are correct." -ForegroundColor Red
  Write-Host ("  - PG_HOST={0}, PG_PORT={1}, PG_DB={2}, PG_USER={3}, PG_PASSWORD=(set)" -f $pgHost,$pgPort,$pgDb,$pgUser) -ForegroundColor DarkGray
  if ($summary) { Write-Host ("  - Backend error: {0}" -f $summary) -ForegroundColor DarkGray }
  # Auto-reinit path on clear auth mismatch indicators
  if ($summary -and ($summary -match 'password authentication failed' -or $summary -match 'FATAL')) {
    Write-Warning "[import] Detected probable password mismatch with existing volume. Reinitializing Postgres volume, then retrying connectivity once ..."
    & (Join-Path $Root 'scripts\db_up.ps1') -ForceReinit
    # Retry a few times
    $ok2 = $false
    for ($j=0; $j -lt 5; $j++) { if (Test-DjangoDbConnection) { $ok2 = $true; break }; Start-Sleep -Seconds 1 }
    if ($ok2) { Write-Host "[import] Connectivity OK after reinit. Proceeding ..." -ForegroundColor DarkGray }
    else {
      Write-Warning "Connectivity still failing after reinit. Will proceed with restore using container-internal psql. Django may still fail until data/schema is restored."
      # fallthrough to continue
    }
  } else {
    Write-Warning "Connectivity probe failed. Proceeding with restore using container-internal psql; will run migrations and re-check afterwards."
    # fallthrough: do not exit here
  }
}

# 2) Restore
# Use hashtable splatting to avoid positional binding of switches like -Latest being treated as FilePath
$restoreParams = @{}
if ($FilePath) { $restoreParams['FilePath'] = $FilePath }
if ($Latest)   { $restoreParams['Latest'] = $true }
if ($SkipDrop) { $restoreParams['SkipDrop'] = $true }
if ($AssumeYes){ $restoreParams['AssumeYes'] = $true } elseif ($Force) { $restoreParams['Force'] = $true }

if (-not $FilePath -and -not $Latest) {
  # Default to latest in backups/
  $restoreParams['Latest'] = $true
}

Write-Host '[import] Restoring backup using scripts/db_restore.ps1 ...' -ForegroundColor DarkGray
& (Join-Path $Root 'scripts\db_restore.ps1') @restoreParams
if ($LASTEXITCODE -ne 0) { Write-Error "Restore failed with exit code $LASTEXITCODE"; exit $LASTEXITCODE }

# Ensure the target DB role password matches backend/.env (some dumps override it)
try {
  $u = $env:PG_USER; if (-not $u -or $u.Trim() -eq '') { $u = 'postgres' }
  $w = $env:PG_PASSWORD; if (-not $w -or $w.Trim() -eq '') { $w = 'postgres' }
  $wSql = $w -replace "'", "''"
  $sql = ('ALTER ROLE "{0}" WITH LOGIN PASSWORD ''{1}'';' -f $u, $wSql)
  Write-Host ("[import] Resetting role password for '{0}' inside container (socket auth) ..." -f $u) -ForegroundColor DarkGray
  $cmd = @('exec', 'pg-sh-school', 'psql', '-U', 'postgres', '-d', 'postgres', '-tAc', $sql)
  $out = & docker @cmd 2>&1
  if ($LASTEXITCODE -ne 0) { Write-Warning ("[import] Password reset command reported non-zero exit. Details: {0}" -f ($out | Out-String)) }
} catch { Write-Warning ("[import] Password reset step skipped: {0}" -f $_.Exception.Message) }

# Verify connectivity again after restore and password reset before running migrations
Write-Host '[import] Verifying Django DB connectivity before migrations ...' -ForegroundColor DarkGray
$okAfterReset = $false
for ($k=0; $k -lt 5; $k++) { if (Test-DjangoDbConnection) { $okAfterReset = $true; break }; Start-Sleep -Seconds 1 }
if (-not $okAfterReset) {
  $summary2 = Get-DjangoDbErrorSummary
  Write-Host "  - PG_HOST=$($env:PG_HOST), PG_PORT=$($env:PG_PORT), PG_DB=$($env:PG_DB), PG_USER=$($env:PG_USER), PG_PASSWORD=(set)" -ForegroundColor DarkGray
  if ($summary2) { Write-Host ("  - Backend error: {0}" -f $summary2) -ForegroundColor DarkGray }
  Write-Error "Cannot establish DB connectivity with Django after restore/password reset. Aborting migrations to avoid noisy stack traces. Verify backend/.env and try: pwsh -File scripts/db_up.ps1 -ForceReinit"
  exit 10
}

# 3) Run Django migrations (safe/idempotent)
Write-Host '[import] Applying Django migrations ...' -ForegroundColor DarkGray
$global:LASTEXITCODE = 0
python backend\manage.py migrate --noinput
$migExit = $LASTEXITCODE
if ($migExit -ne 0) { Write-Error "migrate exited with code $migExit"; exit $migExit }

# 4) Ensure superuser (best-effort from backend/.env)
try {
  $envFile = Join-Path $Root 'backend\.env'
  $envVars = @{}
  if (Test-Path -LiteralPath $envFile) {
    Get-Content $envFile | Where-Object { $_ -and ($_ -notmatch '^\s*#') } | ForEach-Object {
      if ($_ -match '^(?<k>[^=\s]+)=(?<v>.*)$') { $envVars[$Matches['k'].Trim()] = $Matches['v'].Trim() }
    }
  }
  $su = $envVars['DJANGO_SUPERUSER_USERNAME']
  if (-not $su -or $su.Trim() -eq '') { $su = 'mesuef' }
  Write-Host ("[import] Ensuring superuser '{0}' ..." -f $su) -ForegroundColor DarkGray
  Push-Location (Join-Path $Root 'backend')
  try { python manage.py ensure_superuser --username $su | Out-Null } catch { Write-Host "[import] ensure_superuser skipped: $($_.Exception.Message)" -ForegroundColor DarkGray }
  Pop-Location
} catch { }

# 5) Quick probe
function Invoke-HealthProbe {
  try {
    $code = @"
import os, sys
p = r'backend'
if p not in sys.path: sys.path.insert(0, p)
os.environ.setdefault('DJANGO_SETTINGS_MODULE','core.settings')
try:
    import django
    django.setup()
    from django.db import connection
    with connection.cursor() as c:
        c.execute('SELECT 1')
        print('DB_OK')
    from django.contrib.auth import get_user_model
    User = get_user_model()
    print('USERS=', User.objects.count())
    raise SystemExit(0)
except Exception as e:
    print(type(e).__name__, e)
    raise SystemExit(1)
"@
    $tmp = New-TemporaryFile
    Set-Content -Path $tmp -Value $code -Encoding UTF8
    $out = & python $tmp 2>&1
    $exit = $LASTEXITCODE
    Remove-Item $tmp -ErrorAction SilentlyContinue
    return @{ exit=$exit; output=($out | Out-String) }
  } catch { return @{ exit=1; output=$_.Exception.Message } }
}

$probe = Invoke-HealthProbe
if ($probe.exit -eq 0) {
  Write-Host "[import] Probe OK: $($probe.output)" -ForegroundColor Green
} else {
  Write-Warning "[import] Probe had issues:\n$($probe.output)"
}

Write-Host "\n== Import completed successfully ==" -ForegroundColor Green
Write-Host "You can now start the app: pwsh -File scripts/dev_up.ps1" -ForegroundColor DarkGray
