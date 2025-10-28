#requires -Version 5.1
<#!
Dev helper: Reset the local PostgreSQL dev database container and volume.
This is destructive for development data. Use when backend/.env POSTGRES_* values
(user/password/port/db) changed and you see authentication failures.
#>
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# Move to repo root
$Root = Resolve-Path (Join-Path $PSScriptRoot '..')
Set-Location $Root

Write-Host '== Dev DB Reset (PostgreSQL) ==' -ForegroundColor Cyan
Write-Host 'This will RECREATE the local Postgres container and DELETE its data volume.' -ForegroundColor Yellow
Write-Host 'Only use this in development. Your production data is NOT affected.' -ForegroundColor Yellow

$confirm = Read-Host 'Type YES to proceed (anything else to cancel)'
if ($confirm -ne 'YES') {
  Write-Host 'Aborted.' -ForegroundColor DarkGray
  exit 0
}

try {
  pwsh -NoProfile -File (Join-Path $Root 'scripts\db_up.ps1') -ForceReinit
} catch {
  Write-Error $_
  exit 1
}

Write-Host 'Dev DB reset done. You can now run: pwsh -File scripts/dev_up.ps1' -ForegroundColor Green
