#requires -Version 5.1
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# Move to project root (parent of this script directory)
$Root = Resolve-Path (Join-Path $PSScriptRoot '..')
Set-Location $Root

# Optionally activate virtual environment if available
$VenvActivate = Join-Path $Root '.venv\Scripts\Activate.ps1'
if (Test-Path $VenvActivate) {
    try {
        . $VenvActivate
    } catch { }
}

# Forward all provided args to Django management command
# Example:
#   scripts\ensure_superuser.ps1 --username admin --email admin@example.com --password "StrongP@ss!"

python backend\manage.py ensure_superuser @args