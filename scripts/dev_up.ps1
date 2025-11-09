#requires -Version 5.1
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# Go to repo root
$Root = Resolve-Path (Join-Path $PSScriptRoot '..')
Set-Location $Root

Write-Host "== Sh-School | Developer Up (All-in-one) ==" -ForegroundColor Cyan
Write-Host ("Repo: {0}" -f $Root)

# 1) Activate virtualenv if present
$venv = Join-Path $Root '.venv\Scripts\Activate.ps1'
if (Test-Path -Path $venv) {
    Write-Host "[dev_up] Activating .venv ..." -ForegroundColor DarkGray
    . $venv
} else {
    Write-Warning "[dev_up] .venv not found. You can create it via: scripts/dev_setup.ps1"
}

# 2) Ensure Python available
try { python --version *> $null } catch { Write-Error "Python not found on PATH"; exit 1 }

# 3) Ensure core requirements (if Django missing)
$hasDjango = $true
try {
    & python -c "import django" *> $null
} catch { $hasDjango = $false }
if (-not $hasDjango) {
    Write-Host "[dev_up] Installing requirements (this may take a few minutes) ..." -ForegroundColor DarkGray
    python -m pip install --upgrade pip
    python -m pip install -r (Join-Path $Root 'requirements.txt')
}

# 4) Load backend/.env
$EnvFile = Join-Path $Root 'backend\.env'
if (-not (Test-Path -Path $EnvFile)) {
    Write-Error "backend/.env not found. Copy backend/.env.example and adjust values."
    exit 1
}
$envVars = @{}
Get-Content $EnvFile | Where-Object { $_ -and ($_ -notmatch '^\s*#') } | ForEach-Object {
    if ($_ -match '^(?<k>[^=\s]+)=(?<v>.*)$') {
        $envVars[$Matches['k'].Trim()] = $Matches['v'].Trim()
    }
}

# 5) Start PostgreSQL container matching .env
Write-Host "[dev_up] Ensuring PostgreSQL is up ..." -ForegroundColor DarkGray
& (Join-Path $Root 'scripts\db_up.ps1')

# 6) Ensure Redis is up (Docker)
$redisName = 'redis-sh'
$redisId = & docker ps -a --filter "name=$redisName" --format '{{.ID}}'
if (-not $redisId) {
    Write-Host "[dev_up] Starting Redis container ($redisName) ..." -ForegroundColor DarkGray
    docker run -d --name $redisName -p 6379:6379 redis:7-alpine | Out-Null
} else {
    $status = & docker inspect -f '{{.State.Status}}' $redisName
    if ($status -ne 'running') {
        Write-Host "[dev_up] Starting existing Redis container ..." -ForegroundColor DarkGray
        docker start $redisName | Out-Null
    } else {
        Write-Host "[dev_up] Redis is already running." -ForegroundColor DarkGray
    }
}

# 7) Apply migrations
Set-Location (Join-Path $Root 'backend')
Write-Host "[dev_up] Applying Django migrations ..." -ForegroundColor DarkGray
python manage.py migrate
if ($LASTEXITCODE -ne 0) { Write-Error "Migrations failed."; exit $LASTEXITCODE }

# 8) Optional superuser bootstrap (with safe fallback)
$suUser = $envVars['DJANGO_SUPERUSER_USERNAME']
if ($suUser) {
    Write-Host "[dev_up] Ensuring superuser '$suUser' ..." -ForegroundColor DarkGray
    if ($envVars['DJANGO_SUPERUSER_EMAIL']) { $env:DJANGO_SUPERUSER_EMAIL = $envVars['DJANGO_SUPERUSER_EMAIL'] }
    if ($envVars['DJANGO_SUPERUSER_PASSWORD']) { $env:DJANGO_SUPERUSER_PASSWORD = $envVars['DJANGO_SUPERUSER_PASSWORD'] }
    $env:DJANGO_SUPERUSER_USERNAME = $suUser
    try { python manage.py ensure_superuser } catch { Write-Warning $_ }
} else {
    # Fallback: if .env does not define a superuser, try to ensure a local default account
    $fallbackUser = 'mesuef'
    Write-Host "[dev_up] No DJANGO_SUPERUSER_USERNAME in .env; attempting to ensure '$fallbackUser' (flags only) ..." -ForegroundColor DarkGray
    try { python manage.py ensure_superuser --username $fallbackUser } catch { Write-Host "[dev_up] ensure_superuser fallback skipped: $($_.Exception.Message)" -ForegroundColor DarkGray }
}

# 9) Bootstrap RBAC and staff links (best-effort)
try { python manage.py bootstrap_rbac } catch { Write-Warning "[dev_up] bootstrap_rbac: $($_.Exception.Message)" }
# Discipline RBAC (idempotent) – runs automatically with dev:up per project policy
try { python manage.py bootstrap_discipline_rbac --with-access } catch { Write-Warning "[dev_up] bootstrap_discipline_rbac: $($_.Exception.Message)" }
try { python manage.py ensure_staff_users } catch { Write-Warning "[dev_up] ensure_staff_users: $($_.Exception.Message)" }
try { python manage.py activate_staff_users } catch { Write-Warning "[dev_up] activate_staff_users: $($_.Exception.Message)" }

# 10) Start RQ worker in a separate PowerShell window
Write-Host "[dev_up] Launching RQ worker window ..." -ForegroundColor DarkGray
$workerScript = Join-Path $Root 'scripts\rq_worker.ps1'
$pwsh = (Get-Command pwsh -ErrorAction SilentlyContinue)?.Source
if (-not $pwsh) { $pwsh = (Get-Command powershell).Source }
Start-Process -FilePath $pwsh -ArgumentList @('-NoExit','-File',"`"$workerScript`"") | Out-Null

# 11) Start HTTPS development server (Uvicorn TLS) in a separate window; fallback to Django runserver
Write-Host "[dev_up] Launching HTTPS dev server window ..." -ForegroundColor DarkGray
$serveHttps = Join-Path $Root 'scripts\serve_https.ps1'
Start-Process -FilePath $pwsh -ArgumentList @('-NoExit','-File',"`"$serveHttps`"") | Out-Null

# 12) Health checks
Write-Host "[dev_up] Waiting for the server to be ready (healthz) ..." -ForegroundColor DarkGray
$maxWait = 30
$ok = $false
for ($i=0; $i -lt $maxWait; $i++) {
    try {
        $resp = Invoke-WebRequest -Uri 'http://127.0.0.1:8000/healthz' -UseBasicParsing -TimeoutSec 2
        if ($resp.StatusCode -eq 200) { $ok = $true; break }
    } catch { Start-Sleep -Milliseconds 800 }
}
if ($ok) {
    Write-Host "[dev_up] Health OK on HTTP: http://127.0.0.1:8000/healthz" -ForegroundColor Green
} else {
    Write-Warning "[dev_up] HTTP health not confirmed; if using HTTPS only, check: https://127.0.0.1:8443/healthz"
}

# 13) Open browser tabs (admin + loads page)
$openUrls = @('http://127.0.0.1:8000/admin/','http://127.0.0.1:8000/loads/','https://127.0.0.1:8443/admin/')
foreach ($u in $openUrls) { try { Start-Process $u | Out-Null } catch {} }

# 14) Final summary
Write-Host ""; Write-Host "== All set ==" -ForegroundColor Green
Write-Host "- Postgres: docker container 'pg-sh-school' (port from backend/.env)"
Write-Host "- Redis: docker container 'redis-sh' on 6379"
Write-Host "- RQ worker: running in separate window (scripts/rq_worker.ps1)"
Write-Host "- Server: HTTPS via Uvicorn on 8443 (fallback HTTP on 8000) in separate window"
Write-Host "- Admin: http://127.0.0.1:8000/admin/ or https://127.0.0.1:8443/admin/"
Write-Host "- Quick smoke: pwsh -File scripts/dev_smoke.ps1 -HttpsOnly"
Write-Host "Tip: To stop containers: docker stop pg-sh-school redis-sh"
