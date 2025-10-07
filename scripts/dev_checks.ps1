Param(
    [string]$Python = "py",
    [string]$PyVersion = "-3.11"
)

# Create and activate a local virtual environment (robust handling)
Write-Host "[dev_checks] Creating virtual environment (.venv) with Python $PyVersion..."
$venvPy = ".\.venv\Scripts\python.exe"
$useVenv = $true
try {
    & $Python $PyVersion -m venv .venv
} catch {
    Write-Warning "[dev_checks] Failed to create venv: $($_.Exception.Message). Will use system Python."
    $useVenv = $false
}

if ($useVenv -and (Test-Path $venvPy)) {
    try {
        . ".\.venv\Scripts\Activate.ps1"
    } catch {
        Write-Warning "[dev_checks] Failed to activate venv. Using system Python."
        $useVenv = $false
    }
}

$PyCmd = if ($useVenv -and (Test-Path $venvPy)) { $venvPy } else { Write-Warning "[dev_checks] venv unavailable; using system Python."; "python" }

& $PyCmd -m pip install -U pip

# Install dev tools (fall back if requirements-dev.txt is missing)
if (Test-Path -Path "requirements-dev.txt") {
    & $PyCmd -m pip install -r requirements-dev.txt
} else {
    & $PyCmd -m pip install ruff mypy pyright pytest
}

Write-Host "[dev_checks] Running ruff..."
& $PyCmd -m ruff check .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[dev_checks] Running mypy..."
& $PyCmd -m mypy .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[dev_checks] Running pyright..."
# Scope pyright to the file we care about to avoid unrelated framework noise
try {
    & $PyCmd -m pyright gen_index.py
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
} catch {
    Write-Warning "[dev_checks] Pyright is not available; skipping."
}

if (Test-Path -Path ".\pytest.ini") {
    Write-Host "[dev_checks] Running pytest..."
    & $PyCmd -m pytest -q
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
} else {
    Write-Host "[dev_checks] pytest.ini not found; skipping tests."
}

Write-Host "[dev_checks] Done."