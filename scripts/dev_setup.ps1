#requires -Version 5.1
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# Resolve project root as parent of this script directory
$Root = Resolve-Path (Join-Path $PSScriptRoot '..')
Set-Location $Root

$VenvPath = Join-Path $Root '.venv'
$PyCfg = Join-Path $VenvPath 'pyvenv.cfg'
$TargetVenvPath = $VenvPath

Write-Host "Project root: $Root"

function Test-VenvHealthy {
    param(
        [Parameter(Mandatory=$true)][string]$Path
    )
    try {
        $cfg = Join-Path $Path 'pyvenv.cfg'
        $activate = Join-Path $Path 'Scripts\\Activate.ps1'
        $py = Join-Path $Path 'Scripts\\python.exe'
        if (-not (Test-Path $cfg)) { return $false }
        if (-not (Test-Path $activate)) { return $false }
        if (-not (Test-Path $py)) { return $false }
        # Check pip availability inside the venv (without activating)
        $pipOk = $false
        try {
            & $py -m pip --version *> $null
            if ($LASTEXITCODE -eq 0) { $pipOk = $true }
        } catch { $pipOk = $false }
        return $pipOk
    } catch { return $false }
}

# Ensure Python is available
try {
    $pyVersion = & python --version 2>$null
    if (-not $pyVersion) { throw }
    Write-Host "Using $pyVersion"
} catch {
    Write-Error "Python is not available on PATH. Please install Python 3.11+ and re-run."
    exit 1
}

# Deactivate current venv if it points to .venv (to avoid file locks)
try {
    if ($env:VIRTUAL_ENV -and (Split-Path -LiteralPath $env:VIRTUAL_ENV -Resolve) -eq (Split-Path -LiteralPath $VenvPath -Resolve)) {
        if (Get-Command deactivate -ErrorAction SilentlyContinue) {
            Write-Host "Deactivating currently active .venv ..."
            deactivate
        }
    }
} catch { }

# Create or repair venv if missing or unhealthy
$needsCreate = $true
if (Test-Path $VenvPath) {
    if (Test-VenvHealthy -Path $VenvPath) {
        $needsCreate = $false
        Write-Host ".venv looks healthy."
    } else {
        Write-Warning ".venv exists but appears to be broken (missing activate/python/pip). Attempting to recreate ..."
        try {
            # Clear ReadOnly attributes first to improve deletion success
            Get-ChildItem -LiteralPath $VenvPath -Recurse -Force -ErrorAction SilentlyContinue | ForEach-Object {
                try { $_.Attributes = 'Archive' } catch { }
            }
            Remove-Item -LiteralPath $VenvPath -Recurse -Force -ErrorAction Stop
            Write-Host "Removed previous .venv"
        } catch {
            Write-Warning "Failed to remove .venv (possibly locked). Falling back to alternate venv path for this session."
            $TargetVenvPath = Join-Path $Root '.venv_fix'
        }
    }
} else {
    $needsCreate = $true
}
if ($needsCreate) {
    Write-Host "Creating virtual environment at $TargetVenvPath ..."
    python -m venv $TargetVenvPath
}

# Activate venv for current process (use target path which may be .venv_fix)
$activate = Join-Path $TargetVenvPath 'Scripts\Activate.ps1'
if (-not (Test-Path $activate)) {
    Write-Error "Activation script not found at $activate"
    exit 1
}
. $activate

if ($TargetVenvPath -ne $VenvPath) {
    Write-Warning "Using alternate virtual environment at '$TargetVenvPath'. You may delete the old '.venv' manually when it is no longer locked, then rename '.venv_fix' to '.venv'."
}

# Ensure pip is available, then upgrade and install dev requirements
$hasPip = $false
try {
    & python -m pip --version *> $null
    if ($LASTEXITCODE -eq 0) { $hasPip = $true }
} catch { $hasPip = $false }
if (-not $hasPip) {
    Write-Warning "pip not found in the virtual environment. Bootstrapping via ensurepip ..."
    python -m ensurepip --upgrade
}
python -m pip install --upgrade pip
if (Test-Path (Join-Path $Root 'requirements-dev.txt')) {
    pip install -r requirements-dev.txt
} else {
    Write-Warning "requirements-dev.txt not found; installing black and flake8 directly"
    pip install "black==24.*" flake8
}

# Run Black check; if it would reformat, apply formatting once
Write-Host "Running Black (check) ..."
$blackCheck = & black --check gen_index.py 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Warning $blackCheck
    Write-Host "Applying Black formatting ..."
    black gen_index.py
}

# Run Flake8
Write-Host "Running Flake8 ..."
flake8 gen_index.py --max-line-length=100

# Run generator check (no write)
Write-Host "Running generator check ..."
python gen_index.py --check

Write-Host "All dev checks completed successfully." -ForegroundColor Green