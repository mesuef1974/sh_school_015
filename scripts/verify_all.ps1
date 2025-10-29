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

.PARAMETER StartBackend
  If set, attempts to start the backend dev server (scripts/serve_https.ps1) in the background before health probes,
  waiting briefly so that /livez and /healthz can respond.

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
  [switch]$SkipPostgresTests,
  [switch]$StartBackend
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Write-Header($msg){ Write-Host "`n==== $msg ====\n" -ForegroundColor Cyan }
function Write-Ok($msg){ Write-Host "[OK] $msg" -ForegroundColor Green }
function Write-Warn($msg){ Write-Host "[WARN] $msg" -ForegroundColor Yellow }
function Write-Err($msg){ Write-Host "[ERR] $msg" -ForegroundColor Red }
function Write-Info($msg){ Write-Host "[INFO] $msg" -ForegroundColor DarkGray }

# Quick port-busy probe (localhost). Returns $true if something is already listening on the port.
function Test-PortBusy([int]$Port){
  try {
    $ok = Test-NetConnection -ComputerName 127.0.0.1 -Port $Port -InformationLevel Quiet -WarningAction SilentlyContinue -ErrorAction SilentlyContinue
    return [bool]$ok
  } catch { return $false }
}

# Find a free TCP port on localhost starting from a base; returns the first free port or the base if none found.
function Find-FreePort([int]$StartPort, [int]$MaxTries = 50){
  $p = [int]$StartPort
  for ($i = 0; $i -lt $MaxTries; $i++) {
    if (-not (Test-PortBusy -Port $p)) { return $p }
    $p++
  }
  return [int]$StartPort
}

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
      # Determine host ports intended for binding
      $pgPort = if ($Env:PG_HOST_PORT -and $Env:PG_HOST_PORT -ne '') { [int]$Env:PG_HOST_PORT } else { 5433 }
      $redisPort = if ($Env:REDIS_HOST_PORT -and $Env:REDIS_HOST_PORT -ne '') { [int]$Env:REDIS_HOST_PORT } else { 6379 }
      # Preflight: auto-select free host ports if defaults are in use
      $conflicts = @()
      $pgBusy = (Test-PortBusy -Port $pgPort)
      $redisBusy = (Test-PortBusy -Port $redisPort)
      if ($pgBusy) { $conflicts += "PostgreSQL:$pgPort" }
      if ($redisBusy) { $conflicts += "Redis:$redisPort" }
      if ($conflicts.Count -gt 0) {
        Write-Warn ("Port(s) in use: {0}. Auto-selecting free ports..." -f ($conflicts -join ', '))
        if ($pgBusy) {
          $newPg = Find-FreePort -StartPort ($pgPort + 1)
          Write-Info ("Using PG_HOST_PORT={0}" -f $newPg)
          $Env:PG_HOST_PORT = "$newPg"
          $pgPort = $newPg
        }
        if ($redisBusy) {
          $newRedis = Find-FreePort -StartPort ($redisPort + 1)
          Write-Info ("Using REDIS_HOST_PORT={0}" -f $newRedis)
          $Env:REDIS_HOST_PORT = "$newRedis"
          $redisPort = $newRedis
        }
      }
      {#CONTINUE_UP#}
        $null = & docker compose -f $compose up -d
        $upExit = $LASTEXITCODE
        if ($upExit -ne 0) {
          Write-Warn "'docker compose up -d' exited with code $upExit"
          Write-Info ("Hint: If PostgreSQL port {0} is occupied, choose another free port and re-run:" -f $pgPort)
          Write-Host "    `$Env:PG_HOST_PORT='5544'" -ForegroundColor DarkGray
          Write-Info ("Hint: If Redis port {0} is occupied, choose another free port and re-run:" -f $redisPort)
          Write-Host "    `$Env:REDIS_HOST_PORT='6380'" -ForegroundColor DarkGray
          Write-Host "    pwsh -File scripts\\verify_all.ps1 -UpServices" -ForegroundColor DarkGray
          Write-Info "Inspect service status with: docker compose -f infra\\docker-compose.yml ps"
          Write-Info "Check recent logs with: docker compose -f infra\\docker-compose.yml logs --no-color --tail=80"
          $results.services = 'FAIL'
        } else {
          # Verify both services are actually running
          $running = (& docker compose -f $compose ps --services --filter "status=running") -split "`r?`n" | Where-Object { $_ -ne '' }
          $expected = @('postgres','redis')
          $missing = @()
          foreach ($svc in $expected) { if ($running -notcontains $svc) { $missing += $svc } }
          if ($missing.Count -gt 0) {
            Write-Warn ("Some services are not running: {0}" -f ($missing -join ', '))
            Write-Info "Hint: If port 5433 is occupied, set PG_HOST_PORT to another port, e.g.: `$Env:PG_HOST_PORT='5544' then re-run with -UpServices"
            Write-Info "You can inspect status with: docker compose -f infra\\docker-compose.yml ps"
            $results.services = 'FAIL'
          } else {
            Write-Ok 'Docker services are up'
            $results.services = 'PASS'
          }
        }
      }
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

# Linters/Formatters (optional, non-blocking)
Write-Header 'Linters (optional, non-blocking)'

# Frontend lint (ESLint) if npm and config are available
try {
  $feDir = Join-Path $Root 'frontend'
  if (Test-Path -Path $feDir -and (Test-Path -Path (Join-Path $feDir 'package.json'))) {
    Push-Location $feDir

    # If frontend deps are not installed, skip FE lint/format cleanly
    $nodeModules = Join-Path $feDir 'node_modules'
    if (-not (Test-Path -Path $nodeModules)) {
      Write-Warn 'Frontend deps not installed; skipping FE lint/format (run: cd frontend; npm ci)'
      $results.fe_lint = 'SKIP'
      $results.fe_format = 'SKIP'
    } else {
      # Detect npm/npx availability
      try { $npm = Get-Command npm -ErrorAction Stop } catch { $npm = $null }
      try { $npx = Get-Command npx -ErrorAction Stop } catch { $npx = $null }

      if ($npm -or $npx) {
        # --- ESLint ---
        $lintExit = 0
        $eslintLocal = Join-Path $feDir 'node_modules/eslint/bin/eslint.js'
        if (Test-Path -Path $eslintLocal) {
          try {
            & node $eslintLocal .
            $lintExit = $LASTEXITCODE
          } catch { $lintExit = 1 }
        } elseif ($npx) {
          try {
            # Fallback to NPX; avoid PS arg parsing pitfalls by passing simple args
            & $npx.Path --yes eslint .
            $lintExit = $LASTEXITCODE
          } catch { $lintExit = 1 }
        } else {
          $lintExit = -1
        }
        if ($lintExit -eq 0) { Write-Ok 'Frontend lint (eslint) passed'; $results.fe_lint = 'PASS' }
        elseif ($lintExit -eq -1) { Write-Warn 'ESLint skipped (no local bin and npx not available)'; $results.fe_lint = 'SKIP' }
        else { Write-Warn 'Frontend lint (eslint) reported issues'; $results.fe_lint = 'WARN' }

        # --- Prettier (check only, non-blocking) ---
        $fmtExit = 0
        $prettierLocal = Join-Path $feDir 'node_modules/prettier/bin/prettier.cjs'
        $prettierGlob = 'src/**/*.{ts,tsx,js,vue,css,scss,md}'
        if (Test-Path -Path $prettierLocal) {
          try {
            & node $prettierLocal --check $prettierGlob
            $fmtExit = $LASTEXITCODE
          } catch { $fmtExit = 1 }
        } elseif ($npx) {
          try {
            & $npx.Path --yes prettier --check $prettierGlob
            $fmtExit = $LASTEXITCODE
          } catch { $fmtExit = 1 }
        } else {
          $fmtExit = -1
        }
        if ($fmtExit -eq 0) { Write-Ok 'Frontend format (prettier --check) OK'; $results.fe_format = 'PASS' }
        elseif ($fmtExit -eq -1) { Write-Warn 'Prettier check skipped (no local bin and npx not available)'; $results.fe_format = 'SKIP' }
        else { Write-Warn 'Frontend format (prettier) suggests changes'; $results.fe_format = 'WARN' }
      } else {
        Write-Warn 'npm/npx not available; skipping frontend lint/format'
        $results.fe_lint = 'SKIP'
        $results.fe_format = 'SKIP'
      }
    }
  } else {
    $results.fe_lint = 'SKIP'
    $results.fe_format = 'SKIP'
  }
} catch {
  Write-Warn 'Frontend lint/format step encountered an error; treating as WARN (non-blocking).'
  if (-not ($results.ContainsKey('fe_lint'))) { $results['fe_lint'] = 'WARN' }
  if (-not ($results.ContainsKey('fe_format'))) { $results['fe_format'] = 'WARN' }
} finally {
  try { Pop-Location } catch {}
}

# Backend lint/format checks (Ruff/Black/isort) if installed
try {
  $ruffOk = $false; try { & $PythonExe -m ruff --version | Out-Null; $ruffOk = $true } catch {}
  $blackOk = $false; try { & $PythonExe -m black --version | Out-Null; $blackOk = $true } catch {}
  $isortOk = $false; try { & $PythonExe -m isort --version | Out-Null; $isortOk = $true } catch {}
  if (-not ($ruffOk -or $blackOk -or $isortOk)) {
    Write-Warn 'Python linters (ruff/black/isort) not installed; skipping backend lint'
    $results.be_lint = 'SKIP'
  } else {
    $allPass = $true
    if ($ruffOk) {
      try { & $PythonExe -m ruff check backend -q; if ($LASTEXITCODE -ne 0) { $allPass = $false; Write-Warn 'Ruff found issues' } else { Write-Ok 'Ruff passed' } } catch { $allPass = $false; Write-Warn 'Ruff check failed' }
    }
    if ($blackOk) {
      try { & $PythonExe -m black --check backend; if ($LASTEXITCODE -ne 0) { $allPass = $false; Write-Warn 'Black found formatting issues' } else { Write-Ok 'Black formatting OK' } } catch { $allPass = $false; Write-Warn 'Black check failed' }
    }
    if ($isortOk) {
      try { & $PythonExe -m isort --check-only backend; if ($LASTEXITCODE -ne 0) { $allPass = $false; Write-Warn 'isort found import order issues' } else { Write-Ok 'isort import order OK' } } catch { $allPass = $false; Write-Warn 'isort check failed' }
    }
    $results.be_lint = if ($allPass) { 'PASS' } else { 'WARN' }
  }
} catch {
  Write-Warn ("Backend lint step failed: {0}" -f $_.Exception.Message)
  $results.be_lint = 'WARN'
}

# 5) Probe health endpoints if a server is up (optional, non-blocking)
Write-Header 'Health endpoint probes (optional)'

# Optionally start backend for probes
if ($StartBackend) {
  try {
    $serve = Join-Path $Root 'scripts\serve_https.ps1'
    if (Test-Path -Path $serve) {
      Write-Info 'Starting backend (serve_https.ps1) briefly to enable probes ...'
      # Launch in a new pwsh/powershell window minimized so it does not block this script
      $shellExe = 'powershell'
      try { if (Get-Command pwsh -ErrorAction Stop) { $shellExe = 'pwsh' } } catch { $shellExe = 'powershell' }
      Start-Process -FilePath $shellExe -ArgumentList @('-NoProfile','-ExecutionPolicy','Bypass','-File', $serve) -WindowStyle Minimized | Out-Null
      Start-Sleep -Seconds 5
    } else {
      Write-Warn 'serve_https.ps1 not found; cannot auto-start backend.'
    }
  } catch {
    Write-Warn ("Failed to auto-start backend: {0}" -f $_.Exception.Message)
  }
}

# Try to discover backend origin selected by scripts/serve_https.ps1
$runtimeDir = Join-Path $Root 'backend\.runtime'
$originFile = Join-Path $runtimeDir 'dev_origin.txt'
$portFile   = Join-Path $runtimeDir 'https_port.txt'
$discoveredOrigin = $null
if (Test-Path -Path $originFile) {
  try {
    $line = (Get-Content -Path $originFile -ErrorAction Stop | Select-Object -First 1)
    if ($line) { $discoveredOrigin = $line.Trim() }
  } catch { }
} elseif (Test-Path -Path $portFile) {
  try {
    $p = [int]((Get-Content -Path $portFile -ErrorAction Stop | Select-Object -First 1))
    if ($p) { $discoveredOrigin = ("https://127.0.0.1:{0}" -f $p) }
  } catch { }
}

$probes = @()
if ($discoveredOrigin) {
  Write-Info ("Discovered backend origin: {0}" -f $discoveredOrigin)
  # If we just started the backend for probes, wait briefly until /livez responds to reduce flakiness
  if ($StartBackend) {
    $probe = ("{0}/livez" -f $discoveredOrigin)
    $ready = $false
    for ($i = 0; $i -lt 20; $i++) {
      try {
        $resp = Invoke-WebRequest -Uri $probe -UseBasicParsing -TimeoutSec 3 -SkipCertificateCheck -ErrorAction Stop
        if ($resp.StatusCode -eq 204 -or $resp.StatusCode -eq 200) { $ready = $true; break }
      } catch { Start-Sleep -Milliseconds 800 }
    }
    if (-not $ready) { Write-Warn 'Backend not ready yet; proceeding with probes anyway.' } else { Write-Ok 'Backend ready for health probes' }
  }
  $probes += @(
    @{ Uri = ("{0}/livez" -f $discoveredOrigin); Https = ($discoveredOrigin -like 'https*') },
    @{ Uri = ("{0}/healthz" -f $discoveredOrigin); Https = ($discoveredOrigin -like 'https*') }
  )
}
# Always include common defaults as fallback
$probes += @(
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
if ($okCount -eq 0) {
  Write-Warn 'No health endpoints responded. Most likely the backend dev server is not running.'
  Write-Info 'Tip: Start the HTTPS backend + Vite via:'
  Write-Host '    pwsh -File scripts\dev_all.ps1' -ForegroundColor DarkGray
  Write-Info 'Or start backend only (HTTPS dev server):'
  Write-Host '    pwsh -File scripts\serve_https.ps1' -ForegroundColor DarkGray
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