#requires -Version 5.1
<#!
Sh-School | Create Containers From Scratch

Purpose:
  Create fresh local development containers starting from zero, primarily PostgreSQL (and optionally Redis),
  reinitializing data volumes safely and aligning credentials with backend/.env.

What it does:
  1) Recreate PostgreSQL dev container and volume (FORCE reinit) via scripts/db_up.ps1
  2) Optionally recreate Redis container fresh on port 6379
  3) Optionally import the latest backup automatically after DB comes up; otherwise, run migrations and ensure a superuser
  4) Print a quick health summary

Usage examples:
  # Fresh Postgres container only
  pwsh -File scripts/container_new.ps1

  # Fresh Postgres + Redis
  pwsh -File scripts/container_new.ps1 -WithRedis

  # Fresh Postgres and import the latest backup automatically (drops schema)
  pwsh -File scripts/container_new.ps1 -ImportLatest -AssumeYes

  # Fresh Postgres + Redis and import latest without dropping current schema (not recommended)
  pwsh -File scripts/container_new.ps1 -WithRedis -ImportLatest -SkipDrop -AssumeYes
!#>
Param(
  [switch]$WithRedis,
  [switch]$ImportLatest,
  [switch]$AssumeYes,
  [switch]$SkipDrop
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# Move to repo root
$Root = Resolve-Path (Join-Path $PSScriptRoot '..')
Set-Location $Root

Write-Host '== Sh-School | Create Containers From Scratch ==' -ForegroundColor Cyan

# Ensure Docker available
try { & docker --version *> $null } catch {
  Write-Error 'Docker CLI is not available. Please install/start Docker Desktop.'
  exit 1
}

# Activate venv if available
$venv = Join-Path $Root '.venv\Scripts\Activate.ps1'
if (Test-Path -LiteralPath $venv) { try { . $venv } catch { } }

# Ensure Python available for later steps
try { python --version *> $null } catch { Write-Error 'Python not found on PATH. Activate .venv first: .\.venv\Scripts\Activate.ps1'; exit 1 }

# 1) Recreate Postgres from scratch (force reinit)
Write-Host '[new] Recreating PostgreSQL container and data volume (force reinit) ...' -ForegroundColor Yellow
& (Join-Path $Root 'scripts\db_up.ps1') -ForceReinit
if ($LASTEXITCODE -ne 0) { Write-Error "Failed to (re)create PostgreSQL container. Exit $LASTEXITCODE"; exit $LASTEXITCODE }

# 2) Optionally recreate Redis
if ($WithRedis) {
  $redisName = 'redis-sh'
  Write-Host '[new] Recreating Redis container ...' -ForegroundColor Yellow
  try {
    $rid = & docker ps -a --filter "name=$redisName" --format '{{.ID}}'
    if ($rid) { & docker rm -f $redisName | Out-Null }
  } catch { }
  & docker run -d --name $redisName -p 6379:6379 redis:7-alpine | Out-Null
  if ($LASTEXITCODE -ne 0) { Write-Warning 'Redis creation reported a non-zero exit. Check Docker logs if needed.' }
}

# Helper: ensure superuser
function Ensure-Superuser {
  try {
    $envFile = Join-Path $Root 'backend\.env'
    $su = 'mesuef'
    if (Test-Path -LiteralPath $envFile) {
      $envVars = @{}
      Get-Content $envFile | Where-Object { $_ -and ($_ -notmatch '^\s*#') } | ForEach-Object {
        if ($_ -match '^(?<k>[^=\s]+)=(?<v>.*)$') { $envVars[$Matches['k'].Trim()] = $Matches['v'].Trim() }
      }
      if ($envVars['DJANGO_SUPERUSER_USERNAME']) { $su = $envVars['DJANGO_SUPERUSER_USERNAME'] }
      if ($envVars['DJANGO_SUPERUSER_EMAIL'])    { $env:DJANGO_SUPERUSER_EMAIL    = $envVars['DJANGO_SUPERUSER_EMAIL'] }
      if ($envVars['DJANGO_SUPERUSER_PASSWORD']) { $env:DJANGO_SUPERUSER_PASSWORD = $envVars['DJANGO_SUPERUSER_PASSWORD'] }
      $env:DJANGO_SUPERUSER_USERNAME = $su
    }
    Push-Location (Join-Path $Root 'backend')
    try { python manage.py ensure_superuser --username $su | Out-Null } finally { Pop-Location }
    Write-Host ("[new] Superuser ensured: '{0}'" -f $su) -ForegroundColor DarkGray
  } catch { Write-Host ("[new] ensure_superuser skipped: {0}" -f $_.Exception.Message) -ForegroundColor DarkGray }
}

# 3) Data: import latest backup OR run migrations
# Export DATABASE_URL from PG_* values in backend/.env (db_up.ps1 has already aligned the container to these)
try {
  $envFile = Join-Path $Root 'backend\.env'
  $vars = @{}
  if (Test-Path -LiteralPath $envFile) {
    Get-Content $envFile | Where-Object { $_ -and ($_ -notmatch '^\s*#') } | ForEach-Object {
      if ($_ -match '^(?<k>[^=\s]+)=(?<v>.*)$') { $vars[$Matches['k'].Trim()] = $Matches['v'].Trim() }
    }
  }
  function ConvertFrom-QuotedValue([string]$s){ if (-not $s){return $s}; $t=$s.Trim(); if($t.Length -ge 2){$f=$t[0];$l=$t[$t.Length-1]; if(($f -eq '"' -and $l -eq '"') -or ($f -eq "'" -and $l -eq "'")){ return $t.Substring(1,$t.Length-2)} }; return $t }
  $h = ConvertFrom-QuotedValue ($vars['PG_HOST']); if (-not $h) { $h = '127.0.0.1' }
  $p = ConvertFrom-QuotedValue ($vars['PG_PORT']); if (-not $p) { $p = '5432' } else { $p = ($p -replace '[^\d]','') }
  if (-not $p) { $p = '5432' }
  # Prefer runtime-selected port from db_up.ps1 if present
  try {
    $RuntimePortFile = Join-Path $Root 'backend\.runtime\pg_port.txt'
    if (Test-Path -LiteralPath $RuntimePortFile) {
      $pRt = (Get-Content -LiteralPath $RuntimePortFile -ErrorAction SilentlyContinue | Select-Object -First 1).Trim()
      if ($pRt) { $p = ($pRt -replace '[^\d]',''); if (-not $p) { $p = '5432' } }
    }
  } catch { }
  $d = ConvertFrom-QuotedValue ($vars['PG_DB']); if (-not $d) { $d = 'sh_school' }
  $u = ConvertFrom-QuotedValue ($vars['PG_USER']); if (-not $u) { $u = 'postgres' }
  $w = ConvertFrom-QuotedValue ($vars['PG_PASSWORD']); if (-not $w) { $w = 'postgres' }
  $env:DATABASE_URL = ("postgresql://{0}:{1}@{2}:{3}/{4}" -f $u, $w, $h, $p, $d)
} catch { }

if ($ImportLatest) {
  Write-Host '[new] Importing latest backup into fresh database ...' -ForegroundColor Yellow
  $importParams = @{}
  $importParams['Latest'] = $true
  if ($AssumeYes) { $importParams['AssumeYes'] = $true }
  if ($SkipDrop)  { $importParams['SkipDrop']  = $true }
  & (Join-Path $Root 'scripts\import_backup.ps1') @importParams
  if ($LASTEXITCODE -ne 0) { Write-Error "Import failed. Exit $LASTEXITCODE"; exit $LASTEXITCODE }
} else {
  Write-Host '[new] Applying Django migrations on fresh database ...' -ForegroundColor Yellow
  Push-Location (Join-Path $Root 'backend')
  try {
    python manage.py migrate --noinput
    if ($LASTEXITCODE -ne 0) { throw "migrate exited with code $LASTEXITCODE" }
  } finally { Pop-Location }
  Ensure-Superuser
}

# 4) Quick health summary
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
    from django.contrib.auth import get_user_model
    User = get_user_model()
    with connection.cursor() as c:
        c.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public'")
        tbls = c.fetchone()[0]
    print('DB_OK tables=', tbls, ' users=', User.objects.count())
    raise SystemExit(0)
except Exception as e:
    print(type(e).__name__, e)
    raise SystemExit(1)
"@
    $tmp = New-TemporaryFile
    Set-Content -Path $tmp -Value $code -Encoding UTF8
    $out = & python $tmp 2>&1
    $codeExit = $LASTEXITCODE
    Remove-Item $tmp -ErrorAction SilentlyContinue
    return @{ exit=$codeExit; output=($out | Out-String) }
  } catch { return @{ exit=1; output=$_.Exception.Message } }
}

$probe = Invoke-HealthProbe
if ($probe.exit -eq 0) {
  Write-Host ("[new] Probe OK: {0}" -f $probe.output.Trim()) -ForegroundColor Green
} else {
  Write-Warning ("[new] Probe reported issues:\n{0}" -f $probe.output)
}

Write-Host ''
Write-Host '== Fresh container setup complete ==' -ForegroundColor Green
Write-Host 'Next:' -ForegroundColor DarkGray
Write-Host '  - Start full dev environment: pwsh -File scripts/dev_up.ps1' -ForegroundColor DarkGray
Write-Host '  - Or run diagnostics:       pwsh -File scripts/docker_diag.ps1' -ForegroundColor DarkGray
