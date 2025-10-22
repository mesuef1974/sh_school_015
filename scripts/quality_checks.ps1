# Requires: PowerShell 5+ or pwsh 7+
# Purpose: One-click developer quality checks for Python (Django) and Frontend (Vue + Vite).
# - Installs dev tools in the project's virtualenv (Python) and uses npx for JS tools.
# - Runs style, type, security, dead code, and tests with sane defaults.
# - Non-destructive: prefers --check-only where applicable.

param(
  [string]$PythonDir = "backend",
  [string]$FrontendDir = "frontend",
  [string]$VenvPath = ".venv",
  [switch]$InstallOnly
)

$ErrorActionPreference = "Stop"

# Resolve repo root and set current directory
$scriptDir = $PSScriptRoot
if (-not $scriptDir -or $scriptDir -eq '') { $scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path }
$repoRoot = Resolve-Path (Join-Path $scriptDir "..")
Set-Location $repoRoot
Write-Host ("Repository root: {0}" -f $repoRoot) -ForegroundColor DarkGray

function Write-Header($text) {
  Write-Host "`n==== $text ====" -ForegroundColor Cyan
}

function Ensure-Venv {
  if (-not (Test-Path $VenvPath)) {
    Write-Header "Creating virtualenv at $VenvPath"
    python -m venv $VenvPath
  } else {
    Write-Host "Virtualenv found at $VenvPath"
  }
}

function Get-VenvActivatePath {
  param([string]$VenvPath)
  $candidates = @(
    (Join-Path $VenvPath "Scripts/Activate.ps1"),  # Windows
    (Join-Path $VenvPath "bin/Activate.ps1")       # Linux/macOS with pwsh
  )
  foreach ($p in $candidates) { if (Test-Path $p) { return $p } }
  throw "Activation script not found under $VenvPath"
}

function Activate-Venv {
  $activate = Get-VenvActivatePath -VenvPath $VenvPath
  Write-Host "Activating virtualenv at $activate"
  . $activate
  python --version
  pip --version
}

function Install-Python-DevTools {
  Write-Header "Installing Python dev tools"
  python -m pip install -U pip
  # Linters, type checkers, security, dead code, tests, profiling
  pip install `
    ruff `
    mypy `
    bandit `
    safety `
    vulture `
    unimport `
    pycln `
    pytest `
    pytest-django `
    django-silk
}

function Install-Project-Requirements {
  Write-Header "Installing project dependencies"
  if (Test-Path "requirements-dev.txt") {
    pip install -r requirements-dev.txt
  } elseif (Test-Path "requirements.txt") {
    pip install -r requirements.txt
  } elseif (Test-Path "backend/requirements-dev.txt") {
    pip install -r backend/requirements-dev.txt
  } elseif (Test-Path "backend/requirements.txt") {
    pip install -r backend/requirements.txt
  } elseif (Test-Path "pyproject.toml") {
    pip install -e .
  } elseif (Test-Path "backend/pyproject.toml") {
    pip install -e backend
  } else {
    Write-Host "No project requirements file found; skipping." -ForegroundColor Yellow
  }
}

function Run-Python-Quality {
  if (-not (Test-Path $PythonDir)) {
    Write-Host "Python directory '$PythonDir' not found. Skipping Python checks." -ForegroundColor Yellow
    return
  }
  Write-Header "Python: Ruff (lint + format check)"
  ruff check $PythonDir
  ruff format --check $PythonDir

  Write-Header "Python: Type checking (mypy)"
  mypy $PythonDir --ignore-missing-imports --no-warn-unused-ignores

  Write-Header "Python: Security scan (bandit)"
  bandit -r $PythonDir -q -x ".venv,backend/.venv,venv,env,**/site-packages,**/dist,**/build"

  Write-Header "Python: Vulnerability scan (safety)"
  safety check --full-report

  Write-Header "Python: Dead/unused code (vulture)"
  vulture $PythonDir --min-confidence 70

  Write-Header "Python: Unused imports (unimport)"
  # Use check-only to avoid modifying code automatically here
  unimport $PythonDir --check

  Write-Header "Python: Import cleaner (pycln)"
  pycln $PythonDir --check

  Write-Header "Python: Tests (pytest)"
  pytest -q --maxfail=1 --disable-warnings
}

function Run-Frontend-Quality {
  if (-not (Test-Path (Join-Path $FrontendDir "package.json"))) {
    Write-Host "Frontend directory '$FrontendDir' does not contain package.json. Skipping Frontend checks." -ForegroundColor Yellow
    return
  }

  Push-Location $FrontendDir
  try {
    Write-Header "Frontend: Installing node modules (npm ci if lockfile exists)"
    try {
      if (Test-Path "package-lock.json") {
        npm ci
      } else {
        npm install
      }
    } catch {
      Write-Host "npm install failed (continuing): $($_.Exception.Message)" -ForegroundColor Yellow
    }

    Write-Header "Frontend: ESLint (Vue/TS if present)"
    # Skip if no config present (ESLint v9 requires eslint.config.* by default)
    $eslintConfigs = @(
      "eslint.config.js","eslint.config.mjs","eslint.config.cjs",
      ".eslintrc",".eslintrc.js",".eslintrc.cjs",".eslintrc.json",".eslintrc.yaml",".eslintrc.yml"
    )
    $hasEslintConfig = $false
    foreach ($c in $eslintConfigs) { if (Test-Path $c) { $hasEslintConfig = $true; break } }
    if ($hasEslintConfig) {
      try {
        # Use npx to avoid adding permanent dev deps first
        npx --yes eslint "src" --ext .js,.jsx,.ts,.tsx,.vue
      } catch {
        Write-Host "ESLint failed (continuing): $($_.Exception.Message)" -ForegroundColor Yellow
      }
    } else {
      Write-Host "No ESLint config detected; skipping ESLint step." -ForegroundColor Yellow
    }

    Write-Header "Frontend: Unused imports/deps detection"
    try {
      # Detect unused files/imports
      npx --yes unimported
      # Detect unused dependencies
      npx --yes depcheck
    } catch {
      Write-Host "Unused imports/deps checks failed (continuing)." -ForegroundColor Yellow
    }

    Write-Header "Frontend: Type checks (vue-tsc if using TS)"
    if (Test-Path "tsconfig.json") {
      try {
        npx --yes vue-tsc --noEmit
      } catch {
        Write-Host "vue-tsc failed (continuing): $($_.Exception.Message)" -ForegroundColor Yellow
      }
    } else {
      Write-Host "No tsconfig.json found; skipping vue-tsc." -ForegroundColor Yellow
    }
  } finally {
    Pop-Location
  }
}

Write-Header "Developer Quality Checks"
Ensure-Venv
Activate-Venv
Install-Python-DevTools
Install-Project-Requirements

# Ensure Django env defaults
if (-not $Env:PYTHONPATH -or $Env:PYTHONPATH -eq '') { $Env:PYTHONPATH = $PythonDir }
if (-not $Env:DJANGO_SETTINGS_MODULE -or $Env:DJANGO_SETTINGS_MODULE -eq '') { $Env:DJANGO_SETTINGS_MODULE = 'core.settings' }

if ($InstallOnly) {
  Write-Host "InstallOnly specified; exiting after tool installation."
  exit 0
}

Run-Python-Quality
Run-Frontend-Quality

Write-Host "`nAll checks finished." -ForegroundColor Green