#requires -Version 5.1
<#!
Sh-School | Docker Diagnostics Helper

Purpose:
  Quick, non-destructive diagnostics to answer: "هل المشكلة من الدوكر؟" (Is the issue with Docker?)

What it checks:
  1) Docker CLI availability and version
  2) Status of required containers: pg-sh-school (Postgres) and redis-sh (Redis)
  3) Effective PG_* from backend/.env (with unquoting and sane defaults)
  4) TCP reachability to PG_HOST:PG_PORT
  5) Postgres in-container auth probe: SELECT 1 via psql
  6) Django DB connectivity probe using the same environment

Exit codes:
  0 = All good (Docker + DB connectivity OK)
  1 = Docker not available
  2 = Postgres container missing or stopped
  3 = PG TCP not reachable
  4 = Postgres auth probe failed (likely password/volume mismatch)
  5 = Django connectivity failed (manage.py cannot connect)

Usage:
  pwsh -File scripts/docker_diag.ps1
!#>
Param(
  [switch]$VerboseLogs
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# Move to repo root
$Root = Resolve-Path (Join-Path $PSScriptRoot '..')
Set-Location $Root
Write-Host '== Sh-School | Docker Diagnostics ==' -ForegroundColor Cyan

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

# 1) Docker CLI
try {
  $dv = (& docker --version)
  Write-Host "Docker: $dv" -ForegroundColor DarkGray
} catch {
  Write-Error 'Docker CLI is not available. Start Docker Desktop and ensure docker is on PATH.'
  exit 1
}

# 2) Containers status
$pgName = 'pg-sh-school'
$rdName = 'redis-sh'
$pgId = & docker ps -a --filter "name=$pgName" --format '{{.ID}}'
$rdId = & docker ps -a --filter "name=$rdName" --format '{{.ID}}'
if (-not $pgId) {
  Write-Error "Container '$pgName' not found. Start it: pwsh -File scripts/db_up.ps1"
  exit 2
}
$pgState = & docker inspect -f '{{.State.Status}}' $pgName
Write-Host ("Postgres container: {0} (state={1})" -f $pgName,$pgState) -ForegroundColor DarkGray
if ($pgState -ne 'running') {
  Write-Error "Postgres container is not running. Start it: pwsh -File scripts/db_up.ps1"
  exit 2
}
if ($rdId) {
  $rdState = & docker inspect -f '{{.State.Status}}' $rdName
  Write-Host ("Redis container: {0} (state={1})" -f $rdName,$rdState) -ForegroundColor DarkGray
} else {
  Write-Host "Redis container '$rdName' not found (optional)." -ForegroundColor DarkYellow
}

# 3) Read backend/.env
$envFile = Join-Path $Root 'backend\.env'
$vars = @{}
if (Test-Path -LiteralPath $envFile) {
  Get-Content $envFile | Where-Object { $_ -and ($_ -notmatch '^\s*#') } | ForEach-Object {
    if ($_ -match '^(?<k>[^=\s]+)=(?<v>.*)$') { $vars[$Matches['k'].Trim()] = $Matches['v'].Trim() }
  }
}
$PG_HOST = ConvertFrom-QuotedValue ($vars['PG_HOST']); if (-not $PG_HOST) { $PG_HOST = '127.0.0.1' }
$PG_PORT = ConvertFrom-QuotedValue ($vars['PG_PORT']); if (-not $PG_PORT) { $PG_PORT = '5432' } else { $PG_PORT = ($PG_PORT -replace '[^\d]','') }
try { $portNum = [int]$PG_PORT } catch { $portNum = 5432 }
if ($portNum -lt 1 -or $portNum -gt 65535) { $portNum = 5432 }
$PG_DB   = ConvertFrom-QuotedValue ($vars['PG_DB']); if (-not $PG_DB) { $PG_DB = 'sh_school' }
$PG_USER = ConvertFrom-QuotedValue ($vars['PG_USER']); if (-not $PG_USER) { $PG_USER = 'postgres' }
$PG_PWD  = ConvertFrom-QuotedValue ($vars['PG_PASSWORD']); if (-not $PG_PWD) { $PG_PWD = 'postgres' }

$env:PG_HOST=$PG_HOST; $env:PG_PORT=[string]$portNum; $env:PG_DB=$PG_DB; $env:PG_USER=$PG_USER; $env:PG_PASSWORD=$PG_PWD
Write-Host ("Using PG settings: host={0} port={1} db={2} user={3}" -f $PG_HOST,$portNum,$PG_DB,$PG_USER) -ForegroundColor Gray

# 4) TCP reachability
try {
  $tcp = (Test-NetConnection -ComputerName $PG_HOST -Port $portNum -WarningAction SilentlyContinue)
  if (-not $tcp.TcpTestSucceeded) {
    Write-Error ("Cannot reach {0}:{1} over TCP. Is port published and free?" -f $PG_HOST,$portNum)
    exit 3
  } else {
    Write-Host ("TCP reachable: {0}:{1}" -f $PG_HOST,$portNum) -ForegroundColor DarkGray
  }
} catch {
  Write-Error ("TCP probe failed: {0}" -f $_.Exception.Message)
  exit 3
}

# 5) In-container Postgres auth probe
function Test-PostgresAuth {
  try {
    $envArgs = @('-e', "PGPASSWORD=$PG_PWD")
    $cmd = @('exec') + $envArgs + @($pgName, 'psql', '-U', $PG_USER, '-d', $PG_DB, '-tAc', 'SELECT 1;')
    $out = & docker @cmd 2>&1
    if ($LASTEXITCODE -ne 0) { return $false }
    return ($out -match '^1\s*$')
  } catch { return $false }
}
if (Test-PostgresAuth) {
  Write-Host 'Postgres auth probe: OK (SELECT 1)' -ForegroundColor Green
} else {
  Write-Host 'Postgres auth probe: FAILED (likely password mismatch with existing volume).' -ForegroundColor Red
  Write-Host 'Hint: Reinitialize volume then retry: pwsh -File scripts/db_up.ps1 -ForceReinit' -ForegroundColor DarkYellow
  if ($VerboseLogs) {
    Write-Host '--- docker logs (last 80 lines) ---' -ForegroundColor DarkGray
    try { & docker logs --tail 80 $pgName } catch {}
  }
  exit 4
}

# 6) Django connectivity probe
function Test-DjangoDbConnection {
  try {
    $BackendPath = Join-Path $Root 'backend'
    $BackendPathEsc = ($BackendPath -replace '\\','\\')
    $code = @"
import os, sys
backend_path = r'$BackendPathEsc'
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)
# Force the expected environment selector and prevent .env from overriding
os.environ['DJANGO_SETTINGS_MODULE'] = 'core.settings'
os.environ['DJANGO_ENV'] = 'dev'
os.environ['DJANGO_READ_DOTENV'] = '0'
# PG_* are taken from the current process environment (set by the PowerShell script) to avoid embedding secrets here.
try:
    import django
    django.setup()
    from django.db import connection
    with connection.cursor() as c:
        c.execute('SELECT 1')
        c.fetchone()
    print('OK')
    raise SystemExit(0)
except Exception as e:
    print(type(e).__name__, e)
    raise SystemExit(1)
"@
    $tmp = New-TemporaryFile
    Set-Content -Path $tmp -Value $code -Encoding UTF8
    $output = & python $tmp 2>&1
    $exit = $LASTEXITCODE
    Remove-Item $tmp -ErrorAction SilentlyContinue
    return @{ ok=($exit -eq 0 -and ($output -match 'OK')); out=($output | Out-String) }
  } catch { return @{ ok=$false; out=$_.Exception.Message } }
}

$probe = Test-DjangoDbConnection
if ($probe.ok) {
  Write-Host 'Django database connectivity: OK' -ForegroundColor Green
  Write-Host 'Conclusion: Docker & DB look healthy. If you still have issues, run: pwsh -File scripts/dev_up.ps1' -ForegroundColor Cyan
  exit 0
} else {
  Write-Host 'Django database connectivity: FAILED' -ForegroundColor Red
  Write-Host ($probe.out.Trim()) -ForegroundColor DarkGray
  Write-Host 'If this is an auth mismatch, run: pwsh -File scripts/db_up.ps1 -ForceReinit' -ForegroundColor DarkYellow
  Write-Host 'Then you can import latest backup: pwsh -File scripts/fix_db.ps1 -AssumeYes' -ForegroundColor DarkYellow
  exit 5
}
