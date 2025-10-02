#requires -Version 5.1
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# Move to project root
$Root = Resolve-Path (Join-Path $PSScriptRoot '..')
Set-Location $Root

Write-Host "[serve] Project root: $Root"

# Ensure virtualenv active (optional)
$VenvActivate = Join-Path $Root '.venv\Scripts\Activate.ps1'
if (Test-Path $VenvActivate) {
    Write-Host "[serve] Activating .venv ..."
    . $VenvActivate
} else {
    Write-Warning "[serve] .venv not found. You can create it with: scripts/dev_setup.ps1"
}

# Ensure Python + pip available
try {
    & python --version *> $null
} catch {
    Write-Error "Python is not available on PATH or in the venv. Aborting."
    exit 1
}

# Read backend/.env
$EnvFile = Join-Path $Root 'backend\.env'
if (-not (Test-Path $EnvFile)) {
    Write-Error "Env file not found at $EnvFile"
    exit 1
}
$envVars = @{}
Get-Content $EnvFile | Where-Object { $_ -and ($_ -notmatch '^\s*#') } | ForEach-Object {
    if ($_ -match '^(?<k>[^=\s]+)=(?<v>.*)$') {
        $k = $Matches['k'].Trim()
        $v = $Matches['v'].Trim()
        $envVars[$k] = $v
    }
}

# Bring up Postgres with matching credentials/port
Write-Host "[serve] Ensuring Postgres container matches .env (PG_*) ..."
& (Join-Path $Root 'scripts\db_up.ps1')

# Move to backend and run migrations
Set-Location (Join-Path $Root 'backend')

Write-Host "[serve] Applying migrations ..."
python manage.py migrate

# Ensure superuser idempotently via a dedicated command
$suUser = $envVars['DJANGO_SUPERUSER_USERNAME']
$suEmail = $envVars['DJANGO_SUPERUSER_EMAIL']
$suPass = $envVars['DJANGO_SUPERUSER_PASSWORD']
if ($suUser -and $suEmail -and $suPass) {
    Write-Host "[serve] Ensuring superuser '$suUser' exists (idempotent) ..."
    $env:DJANGO_SUPERUSER_USERNAME = $suUser
    $env:DJANGO_SUPERUSER_EMAIL = $suEmail
    $env:DJANGO_SUPERUSER_PASSWORD = $suPass
    # Use custom management command that creates/updates quietly when already present
    python manage.py ensure_superuser
}

# Bootstrap RBAC
Write-Host "[serve] Bootstrapping RBAC groups/permissions ..."
try {
    python manage.py bootstrap_rbac
} catch {
    Write-Warning "[serve] RBAC bootstrap failed: $($_.Exception.Message)"
}

# Optional: collectstatic (dev typically not required)
# Write-Host "[serve] Collecting static files ..."
# python manage.py collectstatic --noinput

# Run server
# Note: avoid using $host (PowerShell reserved automatic variable $Host)
$runHost = if ($envVars['DJANGO_RUN_HOST']) { $envVars['DJANGO_RUN_HOST'] } else { '0.0.0.0' }
$runPort = if ($envVars['DJANGO_RUN_PORT']) { $envVars['DJANGO_RUN_PORT'] } else { '8000' }
Write-Host "[serve] Starting development server at http://$runHost`:$runPort ..." -ForegroundColor Green
python manage.py runserver "$runHost`:$runPort"