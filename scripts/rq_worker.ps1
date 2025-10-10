Param(
    [string]$Queue = "default",
    [string]$RedisHost = "127.0.0.1",
    [int]$Port = 6379
)

$ErrorActionPreference = "Stop"

Write-Host "== RQ Worker Helper ==" -ForegroundColor Cyan
Write-Host "Queue: $Queue" -ForegroundColor DarkGray

# Ensure we are operating from the repository root regardless of the current directory
# Resolve root as parent of this script directory
$Root = Resolve-Path (Join-Path $PSScriptRoot '..')
Set-Location $Root

# Sanity check for backend/manage.py
if (-not (Test-Path -Path "backend\manage.py")) {
    Write-Error "Cannot locate backend\\manage.py. Make sure the repository is intact."
    exit 1
}

# Activate venv if present and not already active
if (-not $env:VIRTUAL_ENV -and (Test-Path -Path ".venv\Scripts\Activate.ps1")) {
    Write-Host "Activating .venv ..." -ForegroundColor DarkGray
    . .\.venv\Scripts\Activate.ps1
}

# Quick Redis connectivity probe
$redisEndpoint = $RedisHost + ":" + $Port
Write-Host ("Probing Redis at {0} ..." -f $redisEndpoint) -ForegroundColor DarkGray
try {
    $tcp = New-Object System.Net.Sockets.TcpClient
    $iar = $tcp.BeginConnect($RedisHost, $Port, $null, $null)
    $ok = $iar.AsyncWaitHandle.WaitOne(2000, $false)
    if (-not $ok -or -not $tcp.Connected) {
        throw ("Cannot connect to Redis at {0}. Is the container running? Try: docker start redis-sh" -f $redisEndpoint)
    }
    $tcp.Close()
} catch {
    Write-Error $_
    exit 2
}

# Apply pending migrations (django_rq tables, etc.)
Write-Host "Applying Django migrations (if any) ..." -ForegroundColor DarkGray
python backend\manage.py migrate
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

# Start worker
Write-Host "Starting RQ worker on queue '$Queue' ..." -ForegroundColor Green
python backend\manage.py rqworker $Queue