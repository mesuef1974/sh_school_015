#requires -Version 5.1
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# Move to project root (parent of this script directory)
$Root = Resolve-Path (Join-Path $PSScriptRoot '..')
Set-Location $Root

# Optional: activate virtual environment if available
$VenvActivate = Join-Path $Root '.venv\Scripts\Activate.ps1'
if (Test-Path -Path $VenvActivate) {
  try { . $VenvActivate } catch { }
}

# Paths
$CertDir = Join-Path $Root 'backend\certs'
$KeyPath = Join-Path $CertDir 'dev.key'
$CrtPath = Join-Path $CertDir 'dev.crt'

Write-Host "== Local HTTPS helper (Uvicorn) ==" -ForegroundColor Cyan
Write-Host "Looking for certificates at:`n  $KeyPath`n  $CrtPath" -ForegroundColor Gray

# --- Preflight: ensure DB is migrated and a superuser exists ---
# Parse backend/.env for optional superuser values
$EnvFile = Join-Path $Root 'backend\.env'
$envVars = @{}  # Always initialize to avoid StrictMode errors when .env is missing or unreadable
if (Test-Path -Path $EnvFile) {
  try {
    Get-Content $EnvFile | Where-Object { $_ -and ($_ -notmatch '^\s*#') } | ForEach-Object {
      if ($_ -match '^(?<k>[^=\s]+)=(?<v>.*)$') { $envVars[$Matches['k'].Trim()] = $Matches['v'].Trim() }
    }
  } catch { Write-Warning "Failed to read backend/.env: $($_.Exception.Message)" }
}

# Apply migrations (idempotent)
try {
  Write-Host "Applying Django migrations (preflight) ..." -ForegroundColor DarkGray
  python backend\manage.py migrate | Out-Null
} catch { Write-Warning "migrate failed (continuing): $($_.Exception.Message)" }

# Ensure superuser (use .env if available, otherwise fallback username 'mesuef')
try {
  if ($envVars -and $envVars['DJANGO_SUPERUSER_USERNAME']) {
    $env:DJANGO_SUPERUSER_USERNAME = $envVars['DJANGO_SUPERUSER_USERNAME']
    if ($envVars['DJANGO_SUPERUSER_EMAIL']) { $env:DJANGO_SUPERUSER_EMAIL = $envVars['DJANGO_SUPERUSER_EMAIL'] }
    if ($envVars['DJANGO_SUPERUSER_PASSWORD']) { $env:DJANGO_SUPERUSER_PASSWORD = $envVars['DJANGO_SUPERUSER_PASSWORD'] }
    Write-Host ("Ensuring superuser '{0}' from .env ..." -f $envVars['DJANGO_SUPERUSER_USERNAME']) -ForegroundColor DarkGray
    python backend\manage.py ensure_superuser | Out-Null
  } else {
    Write-Host "Ensuring fallback superuser 'mesuef' (flags only) ..." -ForegroundColor DarkGray
    python backend\manage.py ensure_superuser --username mesuef | Out-Null
  }
} catch { Write-Host "ensure_superuser skipped: $($_.Exception.Message)" -ForegroundColor DarkGray }

# Ensure certs exist (best-effort auto-generate)
if (-not ((Test-Path -Path $KeyPath) -and (Test-Path -Path $CrtPath))) {
  Write-Host "Certificates not found. Attempting to generate via scripts\\make_dev_cert.ps1 ..." -ForegroundColor Yellow
  $MakeCert = Join-Path $Root 'scripts\make_dev_cert.ps1'
  if (Test-Path -Path $MakeCert) {
    try {
      & "powershell" -NoProfile -ExecutionPolicy Bypass -File $MakeCert
    } catch {
      Write-Warning "make_dev_cert.ps1 failed: $($_.Exception.Message)"
    }
  } else {
    Write-Warning "Helper script not found: $MakeCert"
  }
}

# Determine TLS port. Allow override via DJANGO_TLS_PORT; auto-pick a free one if busy.
$BaseTlsPort = if ($Env:DJANGO_TLS_PORT) { [int]$Env:DJANGO_TLS_PORT } else { 8443 }
function Test-PortInUse([int]$Port){
  try { (Test-NetConnection -ComputerName '127.0.0.1' -Port $Port -WarningAction SilentlyContinue).TcpTestSucceeded } catch { $false }
}
$TlsPort = $BaseTlsPort
if (Test-PortInUse $TlsPort) {
  foreach ($p in (8443..8450)) { if (-not (Test-PortInUse $p)) { $TlsPort = $p; break } }
}

# Try to start Uvicorn with TLS
# Allow overriding log level via DJANGO_UVICORN_LOG_LEVEL (default: info)
$LogLevel = if ($Env:DJANGO_UVICORN_LOG_LEVEL) { $Env:DJANGO_UVICORN_LOG_LEVEL } else { 'info' }

# Friendly hint before launching
$suName = if ($envVars -and $envVars['DJANGO_SUPERUSER_USERNAME']) { $envVars['DJANGO_SUPERUSER_USERNAME'] } else { 'mesuef' }
Write-Host ("Admin login URL: https://127.0.0.1:{0}/admin/  (user: {1})" -f $TlsPort, $suName) -ForegroundColor DarkGray

$UvicornArgs = @(
  '-m','uvicorn','--app-dir','backend','core.asgi:application',
  '--host','0.0.0.0','--port',"$TlsPort",
  '--ssl-keyfile', $KeyPath,
  '--ssl-certfile', $CrtPath,
  '--lifespan','off',
  '--log-level', $LogLevel
)

$canTryTls = (Test-Path -Path $KeyPath) -and (Test-Path -Path $CrtPath)
if ($canTryTls) {
  Write-Host ("Starting HTTPS server on https://0.0.0.0:{0} (Uvicorn + TLS) ..." -f $TlsPort) -ForegroundColor Green
  try {
    # Run in-foreground; if it exits with error, we will fall back to Django dev server
    python @UvicornArgs
    $code = $LASTEXITCODE
  } catch {
    $code = 1
  }
  if ($code -eq 0) {
    exit 0
  } else {
    Write-Warning "Uvicorn HTTPS exited with code $code. Falling back to Django runserver (HTTP)."
  }
} else {
  Write-Warning "TLS certs not available. Falling back to Django runserver (HTTP)."
}

# Fallback: plain HTTP dev server
$HostHttp = if ($Env:DJANGO_RUN_HOST) { $Env:DJANGO_RUN_HOST } else { '0.0.0.0' }
$PortHttp = if ($Env:DJANGO_RUN_PORT) { $Env:DJANGO_RUN_PORT } else { '8000' }
$Url = ("http://{0}:{1}" -f $HostHttp, $PortHttp)
Write-Host "Starting plain HTTP dev server at $Url ..." -ForegroundColor Yellow
python backend\manage.py runserver "$($HostHttp):$($PortHttp)"