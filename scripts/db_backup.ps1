#requires -Version 5.1
param(
    [string]$OutDir,
    [switch]$Gzip
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# Resolve project root as parent of this script directory
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

# Output directory (default: <root>\backups)
if (-not $OutDir) {
    $OutDir = Join-Path $Root 'backups'
}
if (-not (Test-Path $OutDir)) { New-Item -ItemType Directory -Path $OutDir | Out-Null }

# Ensure Docker available
try {
    & docker --version *> $null
} catch {
    Write-Error "Docker CLI is not available. Please install/start Docker Desktop."
    exit 1
}

$containerName = 'pg-sh-school'

# Ensure container exists and is running
$cid = & docker ps -a --filter "name=$containerName" --format '{{.ID}}'
if (-not $cid) {
    Write-Error "Container '$containerName' not found. Start it via scripts/serve.ps1 or scripts/db_up.ps1 first."
    exit 2
}
$running = & docker ps --filter "name=$containerName" --format '{{.ID}}'
if (-not $running) {
    Write-Host "Starting container $containerName ..."
    & docker start $containerName | Out-Null
}

$ts = Get-Date -Format 'yyyyMMdd_HHmmss'
$baseName = "pg_backup_${pgDb}_$ts"
$containerTmp = if ($Gzip) { "/tmp/${baseName}.sql.gz" } else { "/tmp/${baseName}.sql" }
$outFile = Join-Path $OutDir (Split-Path -Leaf $containerTmp)

Write-Host "Creating database backup of '$pgDb' from container '$containerName' ..."

# Build command to run inside container
if ($Gzip) {
    $innerCmd = "PGPASSWORD='$pgPass' pg_dump -U '$pgUser' -d '$pgDb' -F p --no-owner --no-privileges | gzip -c > '$containerTmp'"
} else {
    $innerCmd = "PGPASSWORD='$pgPass' pg_dump -U '$pgUser' -d '$pgDb' -F p --no-owner --no-privileges > '$containerTmp'"
}

# Execute dump inside container
& docker exec -u postgres $containerName sh -lc $innerCmd

# Copy file to host
$srcPath = ($containerName + ':' + $containerTmp)
$dstPath = $outFile
& docker cp $srcPath $dstPath

# Clean up temp file in container (best-effort)
try { & docker exec $containerName rm -f "$containerTmp" } catch { }

Write-Host "Backup completed: $outFile" -ForegroundColor Green

# Provide brief restore hint
Write-Host "Restore (plain SQL): psql -h 127.0.0.1 -U $pgUser -d $pgDb -f `"$outFile`"" -ForegroundColor DarkCyan
if ($Gzip) {
    Write-Host "Restore (gz): gunzip -c `"$outFile`" | psql -h 127.0.0.1 -U $pgUser -d $pgDb" -ForegroundColor DarkCyan
}