#requires -Version 5.1
<#!
Sh-School | Recover Environment (Hard Reset)

Purpose:
  - Recreate local Docker services from scratch (PostgreSQL and Redis)
  - Import the latest database backup automatically
  - Start the full dev environment (backend + frontend)

Usage:
  pwsh -File scripts/recover_env.ps1
!#>
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# Move to repo root
$Root = Resolve-Path (Join-Path $PSScriptRoot '..')
Set-Location $Root

Write-Host '== Sh-School | Recover Environment (Hard Reset) ==' -ForegroundColor Cyan

# 1) Recreate containers (Postgres + Redis) and import latest backup
try {
  $containerNew = Join-Path $Root 'scripts\container_new.ps1'
  if (-not (Test-Path -LiteralPath $containerNew)) { throw "Missing: $containerNew" }
  Write-Host '[recovery] Recreating containers and restoring latest backup ...' -ForegroundColor Yellow
  & pwsh -File $containerNew -WithRedis -ImportLatest -AssumeYes
  if ($LASTEXITCODE -ne 0) { throw "container_new.ps1 failed with exit code $LASTEXITCODE" }
} catch {
  Write-Error ("Recovery step failed: {0}" -f $_.Exception.Message)
  exit 1
}

# 2) Start full dev environment
try {
  $devAll = Join-Path $Root 'scripts\dev_all.ps1'
  if (-not (Test-Path -LiteralPath $devAll)) { throw "Missing: $devAll" }
  Write-Host '[recovery] Starting full dev environment ...' -ForegroundColor Yellow
  & pwsh -File $devAll
} catch {
  Write-Warning ("Failed to start dev environment automatically: {0}" -f $_.Exception.Message)
}

Write-Host ''
Write-Host 'Next steps:' -ForegroundColor DarkGray
Write-Host '  - افتح http://localhost:5173' -ForegroundColor DarkGray
Write-Host "  - جرّب الدخول بالحساب الافتراضي: mesuef / Admin@12345" -ForegroundColor DarkGray
Write-Host '  - إذا فشل الدخول، أرسل حالة ورد POST /api/v1/auth/login/ وسجل الباك-إند الأخير.' -ForegroundColor DarkGray
