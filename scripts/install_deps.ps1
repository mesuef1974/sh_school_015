#requires -Version 5.1
# Install all required libraries for backend (Python) and frontend (Node) in one step.
# - Ensures a local Python virtual environment (.venv) exists and is activated for the current session.
# - Installs backend dependencies from requirements.txt (and requirements-dev.txt when -Dev is passed).
# - Installs frontend dependencies using npm install in the frontend folder (if Node.js/npm are available).
# Usage:
#   pwsh -File scripts/install_deps.ps1                # Install prod deps (Python + Frontend)
#   pwsh -File scripts/install_deps.ps1 -Dev           # Include dev/test tools as well
param(
  [switch]$Dev
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Write-Ok($msg){ Write-Host "[OK] $msg" -ForegroundColor Green }
function Write-Err($msg){ Write-Host "[ERR] $msg" -ForegroundColor Red }
function Write-Info($msg){ Write-Host "[INFO] $msg" -ForegroundColor DarkGray }
function Write-Warn($msg){ Write-Host "[WARN] $msg" -ForegroundColor Yellow }

# Move to repo root
$Root = Resolve-Path (Join-Path $PSScriptRoot '..')
Set-Location $Root

# ---- Python / Backend ----
Write-Host "== Backend (Python) ==" -ForegroundColor Cyan

# Find Python
$pythonExe = $null
try { $pythonExe = (Get-Command python -ErrorAction Stop).Source } catch {}
if (-not $pythonExe) { try { $pythonExe = (Get-Command py -ErrorAction Stop).Source } catch {} }
if (-not $pythonExe) { Write-Err 'Python is not available on PATH. Please install Python 3.11+.'; exit 1 }

# Ensure venv exists
$venvPath = Join-Path $Root '.venv'
$venvActivate = Join-Path $venvPath 'Scripts\Activate.ps1'
if (-not (Test-Path $venvActivate)) {
  Write-Info 'Creating virtual environment (.venv) ...'
  & $pythonExe -m venv $venvPath
  if ($LASTEXITCODE -ne 0) { Write-Err 'Failed to create virtual environment'; exit 1 }
}

# Activate venv
try { . $venvActivate } catch { Write-Err "Failed to activate .venv: $($_.Exception.Message)"; exit 1 }

# Upgrade pip, wheel, setuptools
try { python -m pip install --upgrade pip setuptools wheel | Out-Null } catch { Write-Warn "pip upgrade failed: $($_.Exception.Message)" }

# Install backend requirements
$reqFile = Join-Path $Root 'requirements.txt'
if (Test-Path $reqFile) {
  Write-Info 'Installing backend requirements (requirements.txt) ...'
  python -m pip install -r $reqFile
  if ($LASTEXITCODE -ne 0) { Write-Err 'pip install failed for requirements.txt'; exit 1 }
} else {
  Write-Warn 'requirements.txt not found. Skipping backend base requirements.'
}

if ($Dev) {
  $reqDev = Join-Path $Root 'requirements-dev.txt'
  if (Test-Path $reqDev) {
    Write-Info 'Installing backend dev requirements (requirements-dev.txt) ...'
    python -m pip install -r $reqDev
    if ($LASTEXITCODE -ne 0) { Write-Err 'pip install failed for requirements-dev.txt'; exit 1 }
  } else {
    Write-Info 'requirements-dev.txt not found. Skipping dev backend packages.'
  }
}

Write-Ok 'Backend dependencies installed.'

# ---- Frontend / Node ----
Write-Host "== Frontend (Node/Vite) ==" -ForegroundColor Cyan
$frontendDir = Join-Path $Root 'frontend'
if (-not (Test-Path $frontendDir)) {
  Write-Warn 'frontend directory not found. Skipping frontend dependencies.'
  exit 0
}

Push-Location $frontendDir
try {
  $npm = $null
  try { $npm = (Get-Command npm -ErrorAction Stop).Source } catch {}
  if (-not $npm) { Write-Warn 'npm is not available on PATH. Install Node.js to set up the frontend.'; Pop-Location; exit 0 }

  if (-not (Test-Path 'package.json')) { Write-Warn 'frontend/package.json not found. Skipping npm install.'; Pop-Location; exit 0 }

  $needsInstall = $false
  if (-not (Test-Path 'node_modules')) { $needsInstall = $true }
  if (-not $needsInstall -and -not (Test-Path 'node_modules\\@tanstack\\vue-query')) { $needsInstall = $true }
  if (-not $needsInstall -and -not (Test-Path 'node_modules\\vue-toastification')) { $needsInstall = $true }

  if ($needsInstall) {
    Write-Info 'Running npm install (this may take a while) ...'
    npm install
    if ($LASTEXITCODE -ne 0) { Write-Err 'npm install failed'; Pop-Location; exit 1 }
  } else {
    Write-Info 'Frontend dependencies already present. Skipping npm install.'
  }

  # Ensure vite is present locally (for editors/imports)
  if (-not (Test-Path 'node_modules\\vite\\package.json')) {
    Write-Info 'Installing local Vite (npm i -D vite) ...'
    try { npm install -D vite } catch { Write-Warn "Failed to install local vite: $($_.Exception.Message)" }
  }

  Write-Ok 'Frontend dependencies installed.'
} finally {
  Pop-Location
}

Write-Host ''
Write-Ok 'All required libraries are installed. You can now run: pwsh -File scripts\ops_run.ps1 -Task dev-all'
