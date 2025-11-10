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

.PARAMETER Parts
  Optional list to run only specific parts. Allowed values:
    services, migrate, tests-sqlite, tests-pg, fe-lint, be-lint, security, probes
  Example: -Parts migrate,tests-sqlite

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
  [switch]$StartBackend,
  [string[]]$Parts
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# Normalize Parts filter and helper to decide which sections to run
$__selected = @{}
if ($Parts -and $Parts.Count -gt 0) {
  foreach ($p in $Parts) {
    if (-not $p) { continue }
    $k = ($p.ToString().Trim().ToLowerInvariant())
    switch ($k) {
      'services' { $__selected['services'] = $true }
      'migrate' { $__selected['migrate'] = $true }
      'tests' { $__selected['tests-sqlite'] = $true; $__selected['tests-pg'] = $true }
      'tests-sqlite' { $__selected['tests-sqlite'] = $true }
      'tests-pg' { $__selected['tests-pg'] = $true }
      'fe' { $__selected['fe-lint'] = $true }
      'fe-lint' { $__selected['fe-lint'] = $true }
      'be' { $__selected['be-lint'] = $true }
      'be-lint' { $__selected['be-lint'] = $true }
      'lint' { $__selected['fe-lint'] = $true; $__selected['be-lint'] = $true }
      'security' { $__selected['security'] = $true }
      'probes' { $__selected['probes'] = $true }
      default { $__selected[$k] = $true }
    }
  }
}
function Should-Run([string]$name){ if (-not $Parts -or $Parts.Count -eq 0) { return $true } return [bool]$__selected[$name.ToLowerInvariant()] }

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
# Try to import shared ops utilities for cross-version HTTP and helpers
$__utils = Join-Path $Root 'scripts\lib\ops_utils.psm1'
if (Test-Path $__utils) { try { Import-Module $__utils -Force -ErrorAction Stop } catch {} }

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
if (Should-Run 'services') {
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
          # Ensure external volume exists for first-run friendliness
          $volName = 'sh_school_pg_data'
          try {
            $existing = (& docker volume ls -q --filter "name=$volName") -split "`r?`n" | Where-Object { $_ -ne '' }
            if (-not ($existing | Where-Object { $_ -eq $volName })) {
              Write-Info ("Creating Docker volume: {0}" -f $volName)
              $null = & docker volume create $volName
            }
          } catch {
            Write-Warn ("Could not verify/create Docker volume '{0}': {1}" -f $volName, $_.Exception.Message)
          }
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
  } else {
    $results.services = 'SKIP'
  }
}

# -- Load backend .env (if present) into environment for consistency with Django --
try {
  $envFile = Join-Path $Root 'backend\.env'
  if (Test-Path -Path $envFile) {
    $lines = Get-Content -Path $envFile -ErrorAction Stop
    foreach ($ln in $lines) {
      if (-not $ln -or $ln.Trim().StartsWith('#')) { continue }
      $eq = $ln.IndexOf('=')
      if ($eq -gt 0) {
        $k = $ln.Substring(0,$eq).Trim()
        $v = $ln.Substring($eq+1).Trim()
        if ($v.StartsWith('"') -and $v.EndsWith('"')) { $v = $v.Trim('"') }
        if (-not [string]::IsNullOrWhiteSpace($k)) { Set-Item -Path ("Env:{0}" -f $k) -Value $v }
      }
    }
  }
} catch { }

# -- Configure DB URL and probe PostgreSQL reachability --
$pgReachable = $true
if ($UpServices) {
  $pgHost = '127.0.0.1'
  $pgPort = if ($Env:PG_HOST_PORT -and $Env:PG_HOST_PORT -ne '') { [int]$Env:PG_HOST_PORT } else { 5433 }
  $dbUrl = ("postgresql://postgres:postgres@{0}:{1}/sh_school" -f $pgHost, $pgPort)
  Write-Info ("Using DATABASE_URL={0}" -f $dbUrl)
  $env:DATABASE_URL = $dbUrl
}
# Try a quick psycopg connection probe (2s timeout) to decide whether to run PG-dependent steps
try {
  $probeScript = @"
import os, sys
try:
    import psycopg
except Exception:
    # psycopg not installed -> assume unreachable to avoid crashing steps
    sys.exit(2)
url = os.environ.get('DATABASE_URL', '').strip()
if not url:
    sys.exit(2)
try:
    with psycopg.connect(url, connect_timeout=2) as conn:
        with conn.cursor() as cur:
            cur.execute('SELECT 1')
            cur.fetchone()
    sys.exit(0)
except Exception:
    sys.exit(3)
"@
  $tmp = [System.IO.Path]::GetTempFileName() + '.py'
  [System.IO.File]::WriteAllText($tmp, $probeScript)
  & $PythonExe $tmp | Out-Null
  $code = $LASTEXITCODE
  try { Remove-Item $tmp -Force -ErrorAction SilentlyContinue } catch {}
  if ($code -ne 0) { $pgReachable = $false; Write-Warn 'PostgreSQL not reachable (DATABASE_URL). Will skip DB-dependent steps.' }
} catch { $pgReachable = $false; Write-Warn 'PostgreSQL probe failed. Will skip DB-dependent steps.' }

# 2) Django checks and migrations (PostgreSQL route)
if (Should-Run 'migrate') {
  Write-Header 'Django checks and migrations (PostgreSQL)'
  $env:DJANGO_SETTINGS_MODULE = 'core.settings'
  if ($pgReachable) {
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
  } else {
    Write-Warn 'PostgreSQL not reachable; skipping manage.py check/migrate for PostgreSQL settings.'
    $results.migrate = 'SKIP'
  }
}

# 3) Pytest (SQLite, fast lane)
if (Should-Run 'tests-sqlite') {
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
} else { $results.pytest_sqlite = 'SKIP' }

# 4) Pytest (PostgreSQL) if not skipped
if (Should-Run 'tests-pg') {
  if (-not $SkipPostgresTests) {
    Write-Header 'Tests (PostgreSQL realistic lane)'
    if (-not $pgReachable) {
      Write-Warn 'PostgreSQL not reachable; skipping PostgreSQL test lane.'
      $results.pytest_pg = 'SKIP'
    } else {
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
  } else {
    Write-Warn 'SkipPostgresTests switch set; skipping PostgreSQL test lane.'
    $results.pytest_pg = 'SKIP'
  }
} else { $results.pytest_pg = 'SKIP' }

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

      if ($npm) {
        # Use package scripts to avoid path/arg issues on Windows
        # First, try to auto-fix formatting and lint issues to reduce noise locally
        try { npm run -s format | Out-Null } catch {}
        try { npm run -s lint:fix | Out-Null } catch {}

        # --- ESLint via npm script ---
        $lintExit = 0
        try {
          npm run -s lint
          $lintExit = $LASTEXITCODE
        } catch { $lintExit = 1 }
        if ($lintExit -eq 0) { Write-Ok 'Frontend lint (npm run lint) passed'; $results.fe_lint = 'PASS' }
        else { Write-Warn 'Frontend lint (npm run lint) reported issues'; $results.fe_lint = 'WARN' }

        # --- Prettier check via npm script ---
        $fmtExit = 0
        try {
          npm run -s format:check
          $fmtExit = $LASTEXITCODE
        } catch { $fmtExit = 1 }
        if ($fmtExit -eq 0) { Write-Ok 'Frontend format (prettier --check) OK'; $results.fe_format = 'PASS' }
        else { Write-Warn 'Frontend format (prettier) suggests changes'; $results.fe_format = 'WARN' }
      } elseif ($npx) {
        # Fallback to NPX direct tools when npm script is unavailable
        $lintExit = 0
        try { & $npx.Path --yes eslint .; $lintExit = $LASTEXITCODE } catch { $lintExit = 1 }
        if ($lintExit -eq 0) { Write-Ok 'Frontend lint (eslint) passed'; $results.fe_lint = 'PASS' } else { Write-Warn 'Frontend lint (eslint) reported issues'; $results.fe_lint = 'WARN' }
        $fmtExit = 0
        $prettierGlob = 'src/**/*.{ts,tsx,js,vue,css,scss,md}'
        try { & $npx.Path --yes prettier --check $prettierGlob; $fmtExit = $LASTEXITCODE } catch { $fmtExit = 1 }
        if ($fmtExit -eq 0) { Write-Ok 'Frontend format (prettier --check) OK'; $results.fe_format = 'PASS' } else { Write-Warn 'Frontend format (prettier) suggests changes'; $results.fe_format = 'WARN' }
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
  try {
    $feDir = Join-Path $Root 'frontend'
    if (Test-Path -Path $feDir) {
      Push-Location $feDir
      try { $npm = Get-Command npm -ErrorAction Stop } catch { $npm = $null }
      if ($npm) {
        if (-not ($results.ContainsKey('fe_lint'))) {
          try { npm run -s lint; if ($LASTEXITCODE -eq 0) { $results.fe_lint = 'PASS' } else { $results.fe_lint = 'WARN' } } catch { if (-not ($results.ContainsKey('fe_lint'))) { $results.fe_lint = 'SKIP' } }
        }
        if (-not ($results.ContainsKey('fe_format'))) {
          try { npm run -s format:check; if ($LASTEXITCODE -eq 0) { $results.fe_format = 'PASS' } else { $results.fe_format = 'WARN' } } catch { if (-not ($results.ContainsKey('fe_format'))) { $results.fe_format = 'SKIP' } }
        }
        if (($results.fe_lint -eq 'PASS') -and ($results.fe_format -eq 'PASS')) {
          Write-Ok 'Frontend lint/format passed via fallback'
        } else {
          Write-Warn 'Frontend lint/format did not fully pass via fallback'
        }
      } else {
        if (-not ($results.ContainsKey('fe_lint'))) { $results.fe_lint = 'SKIP' }
        if (-not ($results.ContainsKey('fe_format'))) { $results.fe_format = 'SKIP' }
      }
    }
  } finally {
    try { Pop-Location } catch {}
  }
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

# 5) Dependency security scans (optional, non-blocking)
Write-Header 'Dependency security scans (optional)'

# Python (pip-audit) — if available
try {
  $pipAuditOk = $false; try { & $PythonExe -m pip_audit --version | Out-Null; $pipAuditOk = $true } catch {}
  if ($pipAuditOk) {
    $paExit = 0
    try {
      & $PythonExe -m pip_audit -r requirements.txt -q
      $paExit = $LASTEXITCODE
    } catch { $paExit = 1 }
    if ($paExit -eq 0) { Write-Ok 'pip-audit (requirements.txt) passed' ; $results.security_py = 'PASS' }
    else { Write-Warn 'pip-audit found issues (review locally or in CI)'; $results.security_py = 'WARN' }
  } else {
    Write-Host '[INFO] pip-audit not installed; skipping Python dependency scan' -ForegroundColor Cyan
    $results.security_py = 'SKIP'
  }
} catch {
  Write-Host ('[INFO] pip-audit step skipped: {0}' -f $_.Exception.Message) -ForegroundColor Cyan
  $results.security_py = 'SKIP'
}

# Frontend (npm audit) — if npm and deps are available
try {
  $feDir = Join-Path $Root 'frontend'
  if (Test-Path -Path $feDir -and (Test-Path -Path (Join-Path $feDir 'package.json'))) {
    Push-Location $feDir
    $nodeModules = Join-Path $feDir 'node_modules'
    if (-not (Test-Path -Path $nodeModules)) {
      Write-Warn 'Frontend deps not installed; skipping npm audit (run: cd frontend; npm ci)'
      $results.security_fe = 'SKIP'
    } else {
      try { $npm = Get-Command npm -ErrorAction Stop } catch { $npm = $null }
      if ($npm) {
        $auditExit = 0
        try {
          cmd /c npm audit --omit=dev --audit-level=high
          $auditExit = $LASTEXITCODE
        } catch { $auditExit = 1 }
        if ($auditExit -eq 0) { Write-Ok 'npm audit (prod, high+) OK'; $results.security_fe = 'PASS' }
        else { Write-Warn 'npm audit reported issues'; $results.security_fe = 'WARN' }
      } else {
        Write-Warn 'npm not available; skipping npm audit'
        $results.security_fe = 'SKIP'
      }
    }
  } else {
    $results.security_fe = 'SKIP'
  }
} catch {
  Write-Warn ('npm audit step failed: {0}' -f $_.Exception.Message)
  $results.security_fe = 'WARN'
} finally {
  try { Pop-Location } catch {}
}

# 6) Probe health endpoints if a server is up (optional, non-blocking)
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
        $resp = Invoke-HttpGetCompat -Uri $probe -TimeoutSec 3 -Insecure:($discoveredOrigin -like 'https*')
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
    $r = Invoke-HttpGetCompat -Uri $p.Uri -TimeoutSec 3 -Insecure:([bool]$p.Https)
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
