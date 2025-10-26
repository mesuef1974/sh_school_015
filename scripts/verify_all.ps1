#requires -Version 5.1
<#!
.SYNOPSIS
  One-click verification that your setup and CI-like checks are OK.

.DESCRIPTION
  Runs a concise suite of checks:
   - Optional: ensure Docker services (PostgreSQL, Redis) are up
   - Django checks + migrations against PostgreSQL (core.settings)
   - Unit tests on SQLite (fast, like CI lane)
   - Optional: Unit tests on PostgreSQL (if reachable)
   - Optional: Probe /livez and /healthz if a server is already running
   - Summary with clear PASS/FAIL statuses

.PARAMETER UpServices
  If set, attempts to start Docker services defined in infra/docker-compose.yml.

.PARAMETER SkipPostgresTests
  If set, skip running pytest against PostgreSQL settings.

.EXAMPLE
  pwsh -File scripts/verify_all.ps1

.EXAMPLE
  pwsh -File scripts/verify_all.ps1 -UpServices

.NOTES
  - Requires Python on PATH and project dependencies installed.
  - Does not start the Django server; it only probes if already running on common dev ports.
#>
param(
  [switch]$UpServices,
  [switch]$SkipPostgresTests
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Write-Header($msg){ Write-Host "`n==== $msg ====\n" -ForegroundColor Cyan }
function Write-Ok($msg){ Write-Host "[OK] $msg" -ForegroundColor Green }
function Write-Warn($msg){ Write-Host "[WARN] $msg" -ForegroundColor Yellow }
function Write-Err($msg){ Write-Host "[ERR] $msg" -ForegroundColor Red }
function Write-Info($msg){ Write-Host "[INFO] $msg" -ForegroundColor DarkGray }

# Move to repo root
$Root = Resolve-Path (Join-Path $PSScriptRoot '..')
Set-Location $Root

# Ensure backend on PYTHONPATH for child processes
$env:PYTHONPATH = (Join-Path $Root 'backend')

# Detect Python interpreter (prefer project venv)
$PythonExe = 'python'
$VenvPython = Join-Path $Root '.venv\Scripts\python.exe'
if (Test-Path $VenvPython) { $PythonExe = $VenvPython }
try { & $PythonExe --version | Out-Null } catch { throw "Python is not available at '$PythonExe' or on PATH" }
Write-Info ("Using Python interpreter: {0}" -f $PythonExe)

# Check pytest availability
$pytestAvailable = $true
try { & $PythonExe -m pytest --version | Out-Null } catch { $pytestAvailable = $false }
if (-not $pytestAvailable) {
  Write-Warn "pytest is not installed for the selected interpreter. To install dev tools:"
  Write-Host "    $PythonExe -m pip install -r requirements-dev.txt" -ForegroundColor DarkGray
}

$results = @{}

# 1) Optionally bring up services
if ($UpServices) {
  Write-Header 'Starting Docker services (PostgreSQL + Redis)'
  $compose = Join-Path $Root 'infra\docker-compose.yml'
  if (-not (Test-Path $compose)) { Write-Err 'infra/docker-compose.yml not found'; $results.services = 'SKIP' }
  else {
    try {
      docker --version | Out-Null
      docker compose -f $compose up -d | Out-Null
      Write-Ok 'Docker services are up'
      $results.services = 'PASS'
    } catch {
      Write-Warn "Failed to start Docker services: $($_.Exception.Message)"
      $results.services = 'FAIL'
    }
  }
}

# 2) Django checks and migrations (PostgreSQL route)
Write-Header 'Django checks and migrations (PostgreSQL)'
$env:DJANGO_SETTINGS_MODULE = 'core.settings'
try {
  & $PythonExe backend/manage.py check | Out-Null
  Write-Ok 'manage.py check passed'
  try {
    & $PythonExe backend/manage.py migrate | Out-Null
    Write-Ok 'migrations applied'
    $results.migrate = 'PASS'
  } catch {
    Write-Err "migrate failed: $($_.Exception.Message)"
    $results.migrate = 'FAIL'
  }
} catch {
  Write-Err "manage.py check failed: $($_.Exception.Message)"
  $results.migrate = 'FAIL'
}

# 3) Pytest (SQLite, fast lane)
Write-Header 'Tests (SQLite fast lane)'
$env:DJANGO_SETTINGS_MODULE = 'core.settings_test'
if (-not $pytestAvailable) {
  Write-Warn 'pytest not available; skipping SQLite test lane (install dev deps to enable)'
  $results.pytest_sqlite = 'SKIP'
} else {
  $sqliteExit = 0
  try {
    & $PythonExe -m pytest -q
    $sqliteExit = $LASTEXITCODE
  } catch { $sqliteExit = 1 }
  if ($sqliteExit -eq 0) { Write-Ok 'pytest (SQLite) passed'; $results.pytest_sqlite = 'PASS' }
  else { Write-Err 'pytest (SQLite) failed'; $results.pytest_sqlite = 'FAIL' }
}

# 4) Pytest (PostgreSQL) if not skipped
if (-not $SkipPostgresTests) {
  Write-Header 'Tests (PostgreSQL realistic lane)'
  $env:DJANGO_SETTINGS_MODULE = 'core.settings'
  if (-not $pytestAvailable) {
    Write-Warn 'pytest not available; skipping PostgreSQL test lane (install dev deps to enable)'
    $results.pytest_pg = 'SKIP'
  } else {
    $pgExit = 0
    try {
      & $PythonExe -m pytest -q
      $pgExit = $LASTEXITCODE
    } catch { $pgExit = 1 }
    if ($pgExit -eq 0) { Write-Ok 'pytest (PostgreSQL) passed'; $results.pytest_pg = 'PASS' }
    else { Write-Warn 'pytest (PostgreSQL) failed (ensure DB is up and .env is correct)'; $results.pytest_pg = 'FAIL' }
  }
}

# 5) Probe health endpoints if a server is up (optional, non-blocking)
Write-Header 'Health endpoint probes (optional)'
$probes = @(
  @{ Uri = 'https://127.0.0.1:8443/livez'; Https = $true },
  @{ Uri = 'https://127.0.0.1:8443/healthz'; Https = $true },
  @{ Uri = 'http://127.0.0.1:8000/livez'; Https = $false },
  @{ Uri = 'http://127.0.0.1:8000/healthz'; Https = $false }
)
$okCount = 0
foreach ($p in $probes) {
  try {
    if ($p.Https) {
      $r = Invoke-WebRequest -Uri $p.Uri -Method GET -TimeoutSec 3 -SkipCertificateCheck -ErrorAction Stop
    } else {
      $r = Invoke-WebRequest -Uri $p.Uri -Method GET -TimeoutSec 3 -ErrorAction Stop
    }
    Write-Ok ("{0} -> {1}" -f $p.Uri, $r.StatusCode)
    $okCount++
  } catch {
    Write-Info ("no response from {0}" -f $p.Uri)
  }
}
$results.health_probes = if ($okCount -gt 0) { 'PASS' } else { 'SKIP' }

# 6) Summary
Write-Header 'Summary'
$map = @{
  'services' = 'Services (Docker)'
  'migrate' = 'Django check+migrate'
  'pytest_sqlite' = 'Tests (SQLite)'
  'pytest_pg' = 'Tests (PostgreSQL)'
  'health_probes' = 'Health endpoints'
}
$fail = $false
foreach ($k in $map.Keys) {
  $label = $map[$k]
  $v = $results[$k]
  if (-not $v) { continue }
  switch ($v) {
    'PASS' { Write-Ok $label }
    'SKIP' { Write-Warn "$label (skipped)" }
    default { Write-Err $label; $fail = $true }
  }
}

if ($fail) { exit 1 } else { exit 0 }
