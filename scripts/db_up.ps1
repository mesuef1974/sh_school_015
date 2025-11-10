#requires -Version 5.1
Param(
    [switch]$ForceReinit
)
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

function ConvertFrom-QuotedValue {
    param([string]$s)
    if (-not $s) { return $s }
    $t = $s.Trim()
    if ($t.Length -ge 2) {
        $first = $t[0]; $last = $t[$t.Length-1]
        if (($first -eq '"' -and $last -eq '"') -or ($first -eq "'" -and $last -eq "'")) {
            return $t.Substring(1, $t.Length - 2)
        }
    }
    return $t
}

# Prefer PG_* variables; fall back to DB_* if PG_* not provided; finally use safe defaults for local dev
$pgUser = ConvertFrom-QuotedValue $envVars['PG_USER']; if (-not $pgUser) { $pgUser = ConvertFrom-QuotedValue $envVars['DB_USER'] }
if (-not $pgUser) { $pgUser = 'postgres' }
$pgPass = ConvertFrom-QuotedValue $envVars['PG_PASSWORD']; if (-not $pgPass) { $pgPass = ConvertFrom-QuotedValue $envVars['DB_PASSWORD'] }
if (-not $pgPass) { $pgPass = 'postgres' }
$pgDb   = ConvertFrom-QuotedValue $envVars['PG_DB']; if (-not $pgDb)   { $pgDb   = ConvertFrom-QuotedValue $envVars['DB_NAME'] }
if (-not $pgDb)   { $pgDb = 'sh_school' }
$pgPort = ConvertFrom-QuotedValue $envVars['PG_PORT']; if (-not $pgPort) { $pgPort = ConvertFrom-QuotedValue $envVars['DB_PORT'] }
if (-not $pgPort) { $pgPort = '5432' }
# Sanitize port: keep digits only (handle inline comments like "5433  # comment"). Default to 5432 if empty after cleanup.
$pgPortSan = ($pgPort -replace '[^\d]', '')
if (-not $pgPortSan) { $pgPortSan = '5432' }
# Validate port range
try { $portNum = [int]$pgPortSan } catch { $portNum = 5432 }
if ($portNum -lt 1 -or $portNum -gt 65535) { $portNum = 5432 }
if ($pgPortSan -ne $pgPort) {
    Write-Warning "[db_up] Port value sanitized from '$pgPort' to '$portNum'. Ensure backend/.env has a plain number."
}
$pgPort = [string]$portNum

# If desired port is busy on host and PG_PORT wasn't explicitly set to a non-default value, auto-pick a free port (root fix to avoid conflicts with local Postgres services)
function Test-HostPortBusy {
    param([int]$Port)
    try { return @(Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue).Count -gt 0 } catch { return $false }
}

$RuntimeDir = Join-Path $Root 'backend\.runtime'
try { if (-not (Test-Path -LiteralPath $RuntimeDir)) { New-Item -ItemType Directory -Path $RuntimeDir -Force | Out-Null } } catch { }
$RuntimePortFile = Join-Path $RuntimeDir 'pg_port.txt'

# Decide whether we can change port automatically
$explicitPortSet = $envVars.ContainsKey('PG_PORT') -or $envVars.ContainsKey('DB_PORT')
if (Test-HostPortBusy -Port ([int]$pgPort)) {
    $original = $pgPort
    if (-not $explicitPortSet -or [int]$pgPort -eq 5432) {
        # Try common alternate port 55432, then scan a small range
        $candidates = @(55432, 55433, 55434, 55435, 55436)
        foreach ($cand in $candidates) {
            if (-not (Test-HostPortBusy -Port $cand)) { $pgPort = [string]$cand; break }
        }
        if ($pgPort -eq $original) {
            # Fallback to first free in range 55000-55100
            for ($cand=55000; $cand -le 55100; $cand++) { if (-not (Test-HostPortBusy -Port $cand)) { $pgPort = [string]$cand; break } }
        }
        if ($pgPort -ne $original) {
            Write-Warning ("[db_up] Host port {0} is busy. Will bind container to free port {1} instead. (Persisted to .runtime/pg_port.txt)" -f $original, $pgPort)
            try { Set-Content -Path $RuntimePortFile -Value $pgPort -Encoding ASCII } catch { }
        } else {
            Write-Warning ("[db_up] Desired port {0} is busy and no alternate free port found in the probed range. The container may fail to start." -f $original)
        }
    } else {
        Write-Warning ("[db_up] Desired port {0} from backend/.env is busy on host. Consider changing PG_PORT or stopping the conflicting service." -f $original)
        try { Set-Content -Path $RuntimePortFile -Value $pgPort -Encoding ASCII } catch { }
    }
} else {
    # Persist the chosen/default port for other scripts to consume
    try { Set-Content -Path $RuntimePortFile -Value $pgPort -Encoding ASCII } catch { }
}

$containerName = 'pg-sh-school'
$volumeName = 'pg-sh-school-data'

function Start-Postgres {
    param([switch]$ForceReinit)

    # Helper: remove container if exists
    $existing = & docker ps -a --filter "name=$containerName" --format '{{.ID}}'
    if ($existing) {
        Write-Host "[db_up] Removing existing container $containerName ..."
        try { & docker rm -f $containerName | Out-Null } catch { }
        # Give Docker a moment to release the volume lock
        Start-Sleep -Milliseconds 300
    }

    if ($ForceReinit) {
        # Ensure data volume is removed after container is gone to avoid 'volume is in use' error
        $volExisting = & docker volume ls -q --filter "name=$volumeName"
        if ($volExisting) {
            Write-Host "[db_up] Removing volume $volumeName to re-initialize cluster (password mismatch or init error) ..."
            $removed = $false
            for ($try=0; $try -lt 5; $try++) {
                & docker volume rm $volumeName 2>$null | Out-Null
                if ($LASTEXITCODE -eq 0) { $removed = $true; break }
                Start-Sleep -Milliseconds 400
            }
            if (-not $removed) {
                Write-Warning "[db_up] Could not remove volume '$volumeName' (still in use?). Will try to recreate container anyway with current credentials."
            }
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

function Test-PostgresAuth {
    try {
        # Validate credentials by running a simple TCP query inside the container to force password auth
        $envArgs = @('-e', "PGPASSWORD=$pgPass")
        # First try the target DB; if it fails (e.g., DB missing), try the default 'postgres' DB
        $cmd1 = @('exec') + $envArgs + @($containerName, 'psql', '-h', '127.0.0.1', '-p', '5432', '-U', $pgUser, '-d', $pgDb, '-tAc', 'SELECT 1;')
        $out1 = & docker @cmd1 2>&1
        if ($LASTEXITCODE -eq 0 -and ($out1 -match '^1\s*$')) { return $true }
        # Fallback
        $cmd2 = @('exec') + $envArgs + @($containerName, 'psql', '-h', '127.0.0.1', '-p', '5432', '-U', $pgUser, '-d', 'postgres', '-tAc', 'SELECT 1;')
        $out2 = & docker @cmd2 2>&1
        if ($LASTEXITCODE -eq 0 -and ($out2 -match '^1\s*$')) { return $true }
        return $false
    } catch { return $false }
}

# First attempt
if ($ForceReinit) {
    $ok = Start-Postgres -ForceReinit
} else {
    $ok = Start-Postgres
}
if (-not $ok) {
    # Retry forcing reinit of the data volume
    $ok2 = Start-Postgres -ForceReinit
    if (-not $ok2) {
        Write-Error "Failed to start Postgres after reinitialization attempt. Please run: docker logs $containerName"
        exit 2
    }
}

# Probe authentication; if it fails, auto-reinitialize once
if (-not (Test-PostgresAuth)) {
    Write-Warning "[db_up] Authentication failed for user '$pgUser' on database '$pgDb'. The existing data volume likely has a different password. Reinitializing volume ..."
    $ok3 = Start-Postgres -ForceReinit
    if (-not $ok3) {
        Write-Error "Failed to start Postgres after auth-mismatch reinitialization. Please run: docker logs $containerName"
        exit 3
    }
    if (-not (Test-PostgresAuth)) {
        Write-Error "Authentication still failing after reinit. Verify PG_* in backend/.env and container logs."
        exit 4
    }
}

Write-Host "Connection string (Django): postgres://${pgUser}:<PASSWORD>@127.0.0.1:${pgPort}/${pgDb}"
