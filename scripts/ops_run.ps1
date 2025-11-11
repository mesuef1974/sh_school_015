#requires -Version 5.1
<#
.SYNOPSIS
  Unified operator entrypoint to execute common project commands safely.

.DESCRIPTION
  Provides a single command to run typical developer/CI tasks without remembering each script.
  It wraps existing scripts with sensible defaults and guardrails.

.USAGE
  pwsh -File scripts/ops_run.ps1 -Task verify           # Run verification suite
  pwsh -File scripts/ops_run.ps1 -Task up-services      # Start Docker (PostgreSQL + Redis) with auto-port selection
  pwsh -File scripts/ops_run.ps1 -Task start-backend    # Start HTTPS backend (Uvicorn TLS) in a new window
  pwsh -File scripts/ops_run.ps1 -Task dev-all          # Start backend then Vite dev server (proxy)
  pwsh -File scripts/ops_run.ps1 -Task stop-services    # Stop Docker services
  pwsh -File scripts/ops_run.ps1 -Task install-deps     # Install required libraries (Python + Frontend)

  # Customize ports if defaults are busy
  $Env:PG_HOST_PORT='5544'; $Env:REDIS_HOST_PORT='6380'
  pwsh -File scripts/ops_run.ps1 -Task up-services

.NOTES
  - This is a thin wrapper that calls existing project scripts:
      scripts/verify_all.ps1, scripts/serve_https.ps1, scripts/dev_all.ps1
  - It will not run arbitrary shell input; tasks are allow-listed by design.
#>
param(
  [Parameter(Mandatory = $true)]
  [ValidateSet('verify','up-services','start-backend','dev-all','stop-services','install-deps','help')]
  [string]$Task,
  [switch]$StartBackend,
  [switch]$SkipPostgresTests,
  [switch]$UpServices,
  [switch]$Dev,
  [string[]]$Parts
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Write-Ok($msg){ Write-Host "[OK] $msg" -ForegroundColor Green }
function Write-Err($msg){ Write-Host "[ERR] $msg" -ForegroundColor Red }
function Write-Info($msg){ Write-Host "[INFO] $msg" -ForegroundColor DarkGray }
function Write-Warn($msg){ Write-Host "[WARN] $msg" -ForegroundColor Yellow }

# Move to repo root
$Root = Resolve-Path (Join-Path $PSScriptRoot '..')
Set-Location $Root

# Helper: test if a TCP port is busy on localhost
function Test-PortBusy([int]$Port){
  try {
    return [bool](Test-NetConnection -ComputerName 127.0.0.1 -Port $Port -InformationLevel Quiet -WarningAction SilentlyContinue -ErrorAction SilentlyContinue)
  } catch { return $false }
}

# Helper: find free port from a starting point
function Find-FreePort([int]$StartPort, [int]$MaxTries = 50){
  $p = [int]$StartPort
  for ($i = 0; $i -lt $MaxTries; $i++) { if (-not (Test-PortBusy -Port $p)) { return $p }; $p++ }
  return [int]$StartPort
}

switch ($Task) {
  'verify' {
    $args = @()
    if ($StartBackend) { $args += '-StartBackend' }
    if ($SkipPostgresTests) { $args += '-SkipPostgresTests' }
    if ($UpServices) { $args += '-UpServices' }
    if ($Parts -and $Parts.Count -gt 0) { $args += '-Parts'; $args += $Parts }
    & pwsh -NoProfile -File (Join-Path $Root 'scripts\verify_all.ps1') @args
    exit $LASTEXITCODE
  }
  'up-services' {
    $compose = Join-Path $Root 'infra\docker-compose.yml'
    if (-not (Test-Path $compose)) { Write-Err 'infra/docker-compose.yml not found'; exit 1 }
    try { docker --version | Out-Null } catch { Write-Err "Docker not available: $($_.Exception.Message)"; exit 1 }

    $pgPort = if ($Env:PG_HOST_PORT -and $Env:PG_HOST_PORT -ne '') { [int]$Env:PG_HOST_PORT } else { 5433 }
    $redisPort = if ($Env:REDIS_HOST_PORT -and $Env:REDIS_HOST_PORT -ne '') { [int]$Env:REDIS_HOST_PORT } else { 6379 }

    $pgBusy = Test-PortBusy -Port $pgPort
    $redisBusy = Test-PortBusy -Port $redisPort
    if ($pgBusy) { $new = Find-FreePort -StartPort ($pgPort + 1); $Env:PG_HOST_PORT = "$new"; Write-Info ("Using PG_HOST_PORT={0}" -f $new) }
    if ($redisBusy) { $new = Find-FreePort -StartPort ($redisPort + 1); $Env:REDIS_HOST_PORT = "$new"; Write-Info ("Using REDIS_HOST_PORT={0}" -f $new) }

    # Ensure external volume required by compose exists (first run friendly)
    $volName = 'sh_school_pg_data'
    try {
      $existing = (& docker volume ls -q --filter "name=$volName") -split "`r?`n" | Where-Object { $_ -ne '' }
      if (-not ($existing | Where-Object { $_ -eq $volName })) {
        Write-Info ("Creating Docker volume: {0}" -f $volName)
        $null = & docker volume create $volName
      }
    } catch {
      Write-Warn ("Could not verify/create Docker volume '{0}': {1}" -f $volName, $_.Exception.Message)
    }

    & docker compose -f $compose up -d
    if ($LASTEXITCODE -ne 0) { Write-Err "docker compose up failed (check output above)."; exit 1 }

    $running = (& docker compose -f $compose ps --services --filter "status=running") -split "`r?`n" | Where-Object { $_ -ne '' }
    foreach ($svc in @('postgres','redis')) {
      if ($running -notcontains $svc) { Write-Err ("Service not running: {0}" -f $svc); exit 1 }
    }
    Write-Ok 'Docker services are up'
    exit 0
  }
  'start-backend' {
    $serve = Join-Path $Root 'scripts\serve_https.ps1'
    if (-not (Test-Path -Path $serve)) { Write-Err 'scripts/serve_https.ps1 not found'; exit 1 }
    # Prefer PowerShell 7 if available
    $shellExe = 'powershell'
    try { if (Get-Command pwsh -ErrorAction Stop) { $shellExe = 'pwsh' } } catch { $shellExe = 'powershell' }
    Start-Process -FilePath $shellExe -ArgumentList @('-NoProfile','-NoExit','-ExecutionPolicy','Bypass','-File', $serve)
    Write-Ok 'Backend dev server started in a new window.'
    exit 0
  }
  'dev-all' {
    $dev = Join-Path $Root 'scripts\dev_all.ps1'
    if (-not (Test-Path -Path $dev)) { Write-Err 'scripts/dev_all.ps1 not found'; exit 1 }
    & pwsh -NoProfile -File $dev
    exit $LASTEXITCODE
  }
  'stop-services' {
    $compose = Join-Path $Root 'infra\docker-compose.yml'
    if (-not (Test-Path $compose)) { Write-Err 'infra/docker-compose.yml not found'; exit 1 }
    $null = & docker compose -f $compose down
    if ($LASTEXITCODE -ne 0) { Write-Err 'docker compose down failed'; exit 1 }
    Write-Ok 'Docker services stopped'
    exit 0
  }
  'install-deps' {
    $inst = Join-Path $Root 'scripts\install_deps.ps1'
    if (-not (Test-Path -Path $inst)) { Write-Err 'scripts/install_deps.ps1 not found'; exit 1 }
    $args = @()
    if ($Dev) { $args += '-Dev' }
    & pwsh -NoProfile -File $inst @args
    exit $LASTEXITCODE
  }
  'help' {
    Write-Host "Usage:" -ForegroundColor Cyan
    Write-Host "  pwsh -File scripts/ops_run.ps1 -Task verify [-StartBackend] [-SkipPostgresTests] [-UpServices] [-Parts parts...]" -ForegroundColor Gray
    Write-Host "  pwsh -File scripts/ops_run.ps1 -Task up-services" -ForegroundColor Gray
    Write-Host "  pwsh -File scripts/ops_run.ps1 -Task start-backend" -ForegroundColor Gray
    Write-Host "  pwsh -File scripts/ops_run.ps1 -Task dev-all" -ForegroundColor Gray
    Write-Host "  pwsh -File scripts/ops_run.ps1 -Task stop-services" -ForegroundColor Gray
    Write-Host "  pwsh -File scripts/ops_run.ps1 -Task install-deps" -ForegroundColor Gray
    Write-Host "  # To include dev/test tools:" -ForegroundColor Gray
    Write-Host "  pwsh -File scripts/ops_run.ps1 -Task install-deps -Dev" -ForegroundColor Gray
    Write-Host ""
    Write-Host "Selective verify (-Parts):" -ForegroundColor Yellow
    Write-Host "  Allowed parts: services, migrate, tests-sqlite, tests-pg, fe-lint, be-lint, security, probes" -ForegroundColor DarkGray
    Write-Host "  Examples:" -ForegroundColor Yellow
    Write-Host "    pwsh -File scripts/ops_run.ps1 -Task verify -Parts services,migrate" -ForegroundColor DarkGray
    Write-Host "    pwsh -File scripts/ops_run.ps1 -Task verify -Parts tests-sqlite" -ForegroundColor DarkGray
    Write-Host "    pwsh -File scripts/ops_run.ps1 -Task verify -Parts tests-pg,fe-lint,be-lint" -ForegroundColor DarkGray
    Write-Host ""
    Write-Host "Port conflicts? Choose free ports then re-run up-services:" -ForegroundColor Yellow
    Write-Host "  `$Env:PG_HOST_PORT='5544'; `$Env:REDIS_HOST_PORT='6380'" -ForegroundColor DarkGray
    Write-Host "  pwsh -File scripts/ops_run.ps1 -Task up-services" -ForegroundColor DarkGray
    exit 0
  }
  default {
    Write-Err "Unknown task: $Task"
    exit 1
  }
}
