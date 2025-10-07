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
# Sanitize PG_PORT: keep digits only (handle inline comments like "5433  # comment"). Default to 5432 if empty after cleanup.
$pgPortSan = ($pgPort -replace '[^\d]', '')
if (-not $pgPortSan) { $pgPortSan = '5432' }
# Validate port range
try { $portNum = [int]$pgPortSan } catch { $portNum = 5432 }
if ($portNum -lt 1 -or $portNum -gt 65535) { $portNum = 5432 }
if ($pgPortSan -ne $pgPort) {
    Write-Warning "[db_up] PG_PORT value sanitized from '$pgPort' to '$portNum'. Ensure backend/.env has a plain number."
}
$pgPort = [string]$portNum

$containerName = 'pg-sh-school'
$volumeName = 'pg-sh-school-data'

function Start-Postgres {
    param([switch]$ForceReinit)

    if ($ForceReinit) {
        $volExisting = & docker volume ls -q --filter "name=$volumeName"
        if ($volExisting) {
            Write-Host "[db_up] Removing volume $volumeName to re-initialize cluster (password mismatch or init error) ..."
            & docker volume rm $volumeName | Out-Null
        }
    }

    # If container exists, remove it to recreate with current envs
    $existing = & docker ps -a --filter "name=$containerName" --format '{{.ID}}'
    if ($existing) {
        Write-Host "[db_up] Removing existing container $containerName ..."
        & docker rm -f $containerName | Out-Null
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

    # Wait until ready or detect common init error
    Write-Host "Waiting for Postgres to accept connections ..."
    $maxAttempts = 30
    for ($i=0; $i -lt $maxAttempts; $i++) {
        Start-Sleep -Seconds 1
        # Use cmd.exe to avoid NativeCommandError when docker writes to stderr; capture both stdout and stderr
        $logs = & cmd /c "docker logs $containerName 2>&1"
        if ($logs -match 'database system is ready to accept connections') {
            Write-Host "Postgres is ready." -ForegroundColor Green
            return $true
        }
        if ($logs -match 'Database is uninitialized and superuser password is not specified') {
            Write-Warning "Detected init error: missing superuser password during previous initialization. Will reinitialize volume and retry once."
            return $false
        }
    }
    Write-Warning "Postgres did not report ready in time. Check logs: docker logs $containerName"
    return $true
}

# First attempt (normal)
$ok = Start-Postgres
if (-not $ok) {
    # Retry forcing reinit of the data volume
    $ok2 = Start-Postgres -ForceReinit
    if (-not $ok2) {
        Write-Error "Failed to start Postgres after reinitialization attempt. Please run: docker logs $containerName"
        exit 2
    }
}

Write-Host "Connection string (Django): postgres://${pgUser}:<PASSWORD>@127.0.0.1:${pgPort}/${pgDb}"