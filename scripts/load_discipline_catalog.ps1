#requires -Version 5.1
Param(
  [string]$File = '',
  [switch]$Purge = $false
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# Move to repo root
$Root = Resolve-Path (Join-Path $PSScriptRoot '..')
Set-Location $Root

# Activate virtualenv if present
$VenvActivate = Join-Path $Root '.venv\Scripts\Activate.ps1'
if (Test-Path -LiteralPath $VenvActivate) { try { . $VenvActivate } catch { } }

Push-Location (Join-Path $Root 'backend')
try {
  $argsList = @('manage.py', 'load_discipline_catalog')
  if ($Purge) { $argsList += '--purge' }
  if ($File -and $File.Trim() -ne '') { $argsList += @('--file', $File) }

  Write-Host 'Loading Discipline Catalog ...' -ForegroundColor Cyan
  if ($env:PYTHON) {
    & $env:PYTHON @argsList
  } else {
    python @argsList
  }
} finally {
  Pop-Location
}
