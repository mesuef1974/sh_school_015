#requires -Version 5.1
param(
    [Parameter(Mandatory=$true)]
    [string]$FilePath,
    [switch]$Force,
    [switch]$SkipDrop
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# Resolve project root as parent of this script directory
$Root = Resolve-Path (Join-Path $PSScriptRoot '..')
Set-Location $Root

# Validate input file
if (-not (Test-Path $FilePath)) {
    Write-Error "Backup file not found: $FilePath"
    exit 1
}

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

# Warn user that this is destructive unless SkipDrop set
if (-not $SkipDrop -and -not $Force) {
    Write-Host "تحذير: سيتم حذف محتوى قاعدة البيانات '$pgDb' ثم استعادتها من النسخة المحددة." -ForegroundColor Yellow
    $ans = Read-Host "هل تريد المتابعة؟ اكتب YES"
    if ($ans -ne 'YES') {
        Write-Host 'تم الإلغاء.'
        exit 0
    }
}

# Ensure Docker available
try { & docker --version *> $null } catch {
    Write-Error 'Docker CLI is not available. Please install/start Docker Desktop.'
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

# Copy file into container temp path
$leaf = Split-Path -Leaf $FilePath
$containerTmp = "/tmp/$leaf"
Write-Host "Copying backup into container: $FilePath -> $($containerName):$containerTmp"
& docker cp $FilePath ($containerName + ':' + $containerTmp)

# Determine if gzip
$IsGzip = $leaf.ToLower().EndsWith('.gz')

# Drop schema public (unless SkipDrop)
if (-not $SkipDrop) {
    Write-Host "Dropping and recreating schema 'public' in database '$pgDb' ..."
    $dropCmd = "PGPASSWORD='$pgPass' psql -U '$pgUser' -d '$pgDb' -v ON_ERROR_STOP=1 -c 'DROP SCHEMA IF EXISTS public CASCADE; CREATE SCHEMA public;'"
    & docker exec -u postgres $containerName sh -lc $dropCmd
}

# Restore
Write-Host "Restoring database '$pgDb' from $leaf ..."
if ($IsGzip) {
    $restoreCmd = "set -e; gzip -dc '$containerTmp' | PGPASSWORD='$pgPass' psql -U '$pgUser' -d '$pgDb' -v ON_ERROR_STOP=1"
} else {
    $restoreCmd = "PGPASSWORD='$pgPass' psql -U '$pgUser' -d '$pgDb' -v ON_ERROR_STOP=1 -f '$containerTmp'"
}
& docker exec -u postgres $containerName sh -lc $restoreCmd

# Clean up temp file in container (best-effort)
try { & docker exec $containerName rm -f "$containerTmp" } catch { }

Write-Host "Database restore completed successfully." -ForegroundColor Green