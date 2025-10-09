#requires -Version 5.1
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# Move to repo root
$Root = Resolve-Path (Join-Path $PSScriptRoot '..')
Set-Location $Root

# Optionally activate venv
$VenvActivate = Join-Path $Root '.venv\Scripts\Activate.ps1'
if (Test-Path $VenvActivate) {
  try { . $VenvActivate } catch { }
}

# Helper to run and echo
function Invoke-Step([string]$Title, [string]$Cmd) {
  Write-Host "`n==== $Title ====" -ForegroundColor Cyan
  # Split the command string into tokens to avoid passing it as a single arg
  $tokens = @()
  if ($Cmd) { $tokens = $Cmd -split '\s+' }
  & python backend\manage.py @tokens
}

# 1) Django system check
Invoke-Step "Django system check" "check"

# 2) Migration status
Invoke-Step "Migrations (plan)" "showmigrations --plan"
Invoke-Step "Migrations (check)" "migrate --check"

# 3) Healthcheck (text)
Invoke-Step "Healthcheck (text)" "healthcheck --format text"

Write-Host "`nFull audit finished." -ForegroundColor Green