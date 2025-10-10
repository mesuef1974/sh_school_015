#requires -Version 5.1
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# Move to project root
$Root = Resolve-Path (Join-Path $PSScriptRoot '..')
Set-Location $Root

Write-Host '== Smoke Check ==' -ForegroundColor Cyan

# Activate venv if present
$Venv = Join-Path $Root '.venv\Scripts\Activate.ps1'
if (Test-Path -Path $Venv) { try { . $Venv } catch { } }

# Ensure Python available
try { python --version *> $null } catch { Write-Error 'Python not found on PATH'; exit 1 }

# Run smoke management command (no external server required)
try {
  python backend\manage.py smoke
  exit $LASTEXITCODE
} catch {
  Write-Error $_
  exit 1
}