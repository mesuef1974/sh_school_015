#requires -Version 5.1
# End-to-end quick smoke for local dev flow
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$Root = Resolve-Path (Join-Path $PSScriptRoot '..')
Set-Location $Root

function Assert-LastExitZero($step){
  if ($LASTEXITCODE -ne 0) { throw "Step failed ($step) with exit code $LASTEXITCODE" }
}

Write-Host "== Install deps (dev) ==" -ForegroundColor Cyan
& pwsh -NoProfile -File (Join-Path $Root 'scripts\ops_run.ps1') -Task install-deps -Dev
Assert-LastExitZero 'install-deps'

Write-Host "== Up services ==" -ForegroundColor Cyan
& pwsh -NoProfile -File (Join-Path $Root 'scripts\ops_run.ps1') -Task up-services
Assert-LastExitZero 'up-services'

Write-Host "== Verify (with services) ==" -ForegroundColor Cyan
& pwsh -NoProfile -File (Join-Path $Root 'scripts\ops_run.ps1') -Task verify -UpServices
Assert-LastExitZero 'verify'

Write-Host "== Stop services ==" -ForegroundColor Cyan
& pwsh -NoProfile -File (Join-Path $Root 'scripts\ops_run.ps1') -Task stop-services
Assert-LastExitZero 'stop-services'

Write-Host "All smoke steps passed." -ForegroundColor Green
