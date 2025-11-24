#requires -Version 5.1
<#
  Start local PostgreSQL using the repo's docker-compose and verify connectivity on host port 5433.
  Usage:
    pwsh -File scripts\start_db.ps1
#>
Param(
  [int]$Port = 5433
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# Move to repo root
$Root = Resolve-Path (Join-Path $PSScriptRoot '..')
Set-Location $Root

# Preconditions: docker available, compose file exists, ensure external volume
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
  Write-Error "Docker CLI not found on PATH. Please install Docker Desktop and try again."; exit 1
}
$composeFile = Join-Path $Root 'infra\docker-compose.yml'
if (-not (Test-Path -Path $composeFile)) {
  Write-Error "Compose file not found: $composeFile"; exit 1
}

# Ensure the external volume exists (as declared in infra/docker-compose.yml)
$VolumeName = 'sh_school_pg_data'
try {
  $existing = (docker volume ls -q --filter "name=^${VolumeName}$")
} catch {
  $existing = ''
}
if (-not $existing) {
  Write-Host "Creating external Docker volume '$VolumeName' ..." -ForegroundColor Yellow
  try {
    docker volume create --name $VolumeName | Out-Null
  } catch {
    Write-Error "Failed to create Docker volume '$VolumeName'. Error: $($_.Exception.Message)"; exit 1
  }
}

Write-Host "Starting PostgreSQL via docker compose (infra\docker-compose.yml) ..." -ForegroundColor Cyan
try {
  docker compose -f $composeFile up -d postgres | Out-Null
} catch {
  Write-Error "Failed to start Postgres service via docker compose. Error: $($_.Exception.Message)"; exit 1
}

Write-Host "Waiting for Postgres to become healthy ..." -ForegroundColor DarkGray
$max = 30
for ($i=0; $i -lt $max; $i++) {
  try {
    $ok = Test-NetConnection -ComputerName 127.0.0.1 -Port $Port -WarningAction SilentlyContinue
    if ($ok.TcpTestSucceeded) { break }
  } catch {}
  Start-Sleep -Seconds 1
}

$svc = (docker compose -f $composeFile ps --format json | ConvertFrom-Json | Where-Object { $_.Name -match 'postgres' })
$health = $null
try { $health = (docker inspect --format='{{json .State.Health.Status}}' $svc.Name) } catch {}

Write-Host "Postgres TCP: $(if($ok.TcpTestSucceeded){'OK'}else{'DOWN'}) on 127.0.0.1:$Port; Health: $health" -ForegroundColor Green

Write-Host "Recommended backend/.env line:" -ForegroundColor Yellow
Write-Host "  DATABASE_URL=postgres://postgres:postgres@127.0.0.1:$Port/sh_school" -ForegroundColor Yellow

Write-Host "You can now run: python manage.py check && python manage.py migrate" -ForegroundColor Cyan
