#requires -Version 5.1
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# Move to project root
$Root = Resolve-Path (Join-Path $PSScriptRoot '..')
Set-Location $Root

# Load backend/.env for PG_* variables
$envFile = Join-Path $Root 'backend\.env'
if (-not (Test-Path $envFile)) {
    Write-Error "Env file not found at $envFile"
    exit 1
}

# Parse .env
$envVars = @{}
Get-Content $envFile | Where-Object { $_ -and ($_ -notmatch '^\s*#') } | ForEach-Object {
    if ($_ -match '^(?<k>[^=\s]+)=(?<v>.*)$') {
        $k = $Matches['k'].Trim()
        $v = $Matches['v'].Trim()
        $envVars[$k] = $v
    }
}

$pgUser = $envVars['PG_USER']; if (-not $pgUser) { $pgUser = 'postgres' }
$pgPass = $envVars['PG_PASSWORD']; if (-not $pgPass) { $pgPass = 'postgres' }
$pgDb   = $envVars['PG_DB']; if (-not $pgDb) { $pgDb = 'sh_school' }
$pgPort = $envVars['PG_PORT']; if (-not $pgPort) { $pgPort = '5432' }

$containerName = 'pg-sh-school'
$volumeName = 'pg-sh-school-data'

# If container exists, stop/remove before recreating (keeps idempotent)
$existing = & docker ps -a --filter "name=$containerName" --format '{{.ID}}'
if ($existing) {
    Write-Host "Container $containerName already exists. Restarting with current env values ..."
    & docker rm -f $containerName | Out-Null
    # Remove the existing named volume to avoid stale credentials/data in dev
    $volExisting = & docker volume ls -q --filter "name=$volumeName"
    if ($volExisting) {
        Write-Host "Removing existing volume $volumeName to re-initialize database cluster ..."
        & docker volume rm $volumeName | Out-Null
    }
}

# Run Postgres pinned to 16, explicit POSTGRES_USER and password
$runArgs = @(
    'run','--name', $containerName,
    '-e', "POSTGRES_USER=$pgUser",
    '-e', "POSTGRES_PASSWORD=$pgPass",
    '-e', "POSTGRES_DB=$pgDb",
    '-p', "${pgPort}:5432",
    '-v', ($volumeName + ':/var/lib/postgresql/data'),
    '-d', 'postgres:16'
)

Write-Host "Starting Postgres container with: user=$pgUser db=$pgDb port=$pgPort"
& docker @runArgs

# Wait until ready
Write-Host "Waiting for Postgres to accept connections ..."
$maxAttempts = 30
for ($i=0; $i -lt $maxAttempts; $i++) {
    Start-Sleep -Seconds 1
    $logs = & docker logs $containerName 2>&1
    if ($logs -match 'database system is ready to accept connections') {
        Write-Host "Postgres is ready." -ForegroundColor Green
        break
    }
    if ($i -eq $maxAttempts-1) {
        Write-Warning "Postgres did not report ready in time. Check logs: docker logs $containerName"
    }
}

Write-Host "Connection string (Django): postgres://${pgUser}:<PASSWORD>@127.0.0.1:${pgPort}/${pgDb}"