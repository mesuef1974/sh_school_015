#requires -Version 5.1
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# Project root is parent of this script dir
$Root = Resolve-Path (Join-Path $PSScriptRoot '..')
Set-Location $Root

# Ensure Python exists
try {
    $pyv = & python --version 2>$null
    if (-not $pyv) { throw }
    Write-Host "Using $pyv"
} catch {
    Write-Error "Python is not available on PATH. Install Python 3.11+ and retry."
    exit 1
}

# Ensure virtual environment exists and is usable
$VenvPath = Join-Path $Root '.venv'
$ActivatePath = Join-Path $VenvPath 'Scripts\Activate.ps1'
if (-not (Test-Path $ActivatePath)) {
    Write-Host "Creating virtual environment at $VenvPath ..."
    python -m venv $VenvPath
}

# Activate venv
. $ActivatePath

# Ensure pip available, then install backend requirements (not dev tools)
try { & python -m pip --version *> $null } catch { python -m ensurepip --upgrade }
python -m pip install --upgrade pip

# Install base requirements
if (Test-Path (Join-Path $Root 'requirements.txt')) {
    Write-Host "Installing base requirements from requirements.txt ..."
    pip install -r requirements.txt
} else {
    Write-Warning "requirements.txt not found at project root: $Root"
}

# Forward all remaining args to manage.py
$ManagePy = Join-Path $Root 'backend\manage.py'
if (-not (Test-Path $ManagePy)) {
    Write-Error "manage.py not found at $ManagePy"
    exit 1
}

# If no args provided, show help
if ($args.Count -eq 0) {
    Write-Host "No arguments provided. Examples:" -ForegroundColor Yellow
    Write-Host "  ./scripts/backend_run.ps1 migrate"
    Write-Host "  ./scripts/backend_run.ps1 runserver 0.0.0.0:8000"
    Write-Host "  ./scripts/backend_run.ps1 import_from_pdf D:\\sh_school_015\\DOC\\school_DATA --dry-run"
    exit 0
}

# Execute the management command with passthrough args
Write-Host "Running: python backend\\manage.py $($args -join ' ')"
& python $ManagePy @args
exit $LASTEXITCODE