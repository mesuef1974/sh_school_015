#requires -Version 5.1
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# ------------- Constants / Defaults -------------
$DEFAULT_TLS_PORT        = 8443
$TLS_PROBE_RANGE         = 8443..8450
$DEFAULT_LOG_LEVEL       = 'info'
$DEFAULT_HTTP_HOST       = '0.0.0.0'
$DEFAULT_HTTP_PORT       = '8000'
$DEV_CERT_REL_DIR        = 'backend\certs'
$DEV_KEY_NAME            = 'dev.key'
$DEV_CRT_NAME            = 'dev.crt'
$ENV_REL_PATH            = 'backend\.env'
$MAKE_CERT_REL_PATH      = 'scripts\make_dev_cert.ps1'
$UVICORN_APP             = 'core.asgi:application'
$UVICORN_APP_DIR         = 'backend'
$VENV_WIN_ACTIVATE_REL   = '.venv\Scripts\Activate.ps1'

# ------------- Location / Venv -------------
$Root = Resolve-Path (Join-Path $PSScriptRoot '..')
Set-Location $Root

$VenvActivate = Join-Path $Root $VENV_WIN_ACTIVATE_REL
if (Test-Path -Path $VenvActivate) {
  try { . $VenvActivate } catch { }
}

# ------------- Paths -------------
$CertDir = Join-Path $Root $DEV_CERT_REL_DIR
$KeyPath = Join-Path $CertDir $DEV_KEY_NAME
$CrtPath = Join-Path $CertDir $DEV_CRT_NAME
$EnvFile = Join-Path $Root $ENV_REL_PATH
$MakeCert = Join-Path $Root $MAKE_CERT_REL_PATH

Write-Host "== Local HTTPS helper (Uvicorn) ==" -ForegroundColor Cyan
Write-Host ("Looking for certificates at:`n  {0}`n  {1}" -f $KeyPath, $CrtPath) -ForegroundColor Gray

# ------------- Helpers -------------
function Read-DotEnv {
  param([string]$Path)
  $result = @{}
  if (-not (Test-Path -Path $Path)) { return $result }
  try {
    Get-Content $Path | Where-Object { $_ -and ($_ -notmatch '^\s*#') } | ForEach-Object {
      if ($_ -match '^(?<k>[^=\s]+)=(?<v>.*)$') {
        $result[$Matches['k'].Trim()] = $Matches['v'].Trim()
      }
    }
  } catch {
    Write-Warning ("Failed to read {0}: {1}" -f $Path, $_.Exception.Message)
  }
  return $result
}

function Invoke-DjangoMigrateIfNeeded {
  try {
    # Check if there are unapplied migrations; if none, skip the heavy migrate step
    Write-Host "Checking Django migrations status ..." -ForegroundColor DarkGray
    $plan = python backend\manage.py showmigrations --plan 2>$null
    if ($LASTEXITCODE -ne 0 -or -not $plan) {
      Write-Host "showmigrations failed - running migrate to be safe." -ForegroundColor DarkYellow
      python backend\manage.py migrate --noinput | Out-Null
      return
    }
    if ($plan -match "\[ \]") {
      Write-Host "Applying Django migrations (changes detected) ..." -ForegroundColor DarkGray
      python backend\manage.py migrate --noinput | Out-Null
    } else {
      Write-Host "Migrations up-to-date - skipping migrate." -ForegroundColor DarkGray
    }
  } catch {
    Write-Warning ("migrate probe failed - running migrate anyway: {0}" -f $_.Exception.Message)
    try { python backend\manage.py migrate --noinput | Out-Null } catch { Write-Warning ("migrate failed: {0}" -f $_.Exception.Message) }
  }
}

function Ensure-Superuser {
  param([hashtable]$DotEnv)
  try {
    if ($DotEnv -and $DotEnv['DJANGO_SUPERUSER_USERNAME']) {
      $env:DJANGO_SUPERUSER_USERNAME = $DotEnv['DJANGO_SUPERUSER_USERNAME']
      if ($DotEnv['DJANGO_SUPERUSER_EMAIL'])    { $env:DJANGO_SUPERUSER_EMAIL    = $DotEnv['DJANGO_SUPERUSER_EMAIL'] }
      if ($DotEnv['DJANGO_SUPERUSER_PASSWORD']) { $env:DJANGO_SUPERUSER_PASSWORD = $DotEnv['DJANGO_SUPERUSER_PASSWORD'] }
      Write-Host ("Ensuring superuser '{0}' from .env ..." -f $DotEnv['DJANGO_SUPERUSER_USERNAME']) -ForegroundColor DarkGray
      python backend\manage.py ensure_superuser | Out-Null
    } else {
      Write-Host "Ensuring fallback superuser 'mesuef' (flags only) ..." -ForegroundColor DarkGray
      python backend\manage.py ensure_superuser --username mesuef | Out-Null
    }
  } catch {
    Write-Host ("ensure_superuser skipped: {0}" -f $_.Exception.Message) -ForegroundColor DarkGray
  }
}

function New-DevCertificatesIfMissing {
  param([string]$Key,[string]$Crt,[string]$GeneratorPath)
  if ((Test-Path -Path $Key) -and (Test-Path -Path $Crt)) { return }
  Write-Host "Certificates not found. Attempting to generate via scripts\make_dev_cert.ps1 ..." -ForegroundColor Yellow
  if (Test-Path -Path $GeneratorPath) {
    try {
      & "powershell" -NoProfile -ExecutionPolicy Bypass -File $GeneratorPath
    } catch {
      Write-Warning ("make_dev_cert.ps1 failed: {0}" -f $_.Exception.Message)
    }
  } else {
    Write-Warning ("Helper script not found: {0}" -f $GeneratorPath)
  }
}

function Test-PortInUse {
  param([int]$Port)
  try {
    return (Test-NetConnection -ComputerName '127.0.0.1' -Port $Port -WarningAction SilentlyContinue).TcpTestSucceeded
  } catch { return $false }
}

function Get-AvailableTlsPort {
  param([int]$Preferred,[int[]]$ProbeRange)
  if (-not (Test-PortInUse -Port $Preferred)) { return $Preferred }
  foreach ($p in $ProbeRange) { if (-not (Test-PortInUse -Port $p)) { return $p } }
  return $Preferred
}

function Start-UvicornTls {
  param(
    [int]$Port,
    [string]$KeyFile,
    [string]$CertFile,
    [string]$LogLevel,
    [string]$App,
    [string]$AppDir
  )
  $args = @(
    '-m','uvicorn','--app-dir', $AppDir, $App,
    '--host','127.0.0.1','--port',"$Port",
    '--ssl-keyfile', $KeyFile,
    '--ssl-certfile', $CertFile,
    '--lifespan','off',
    '--log-level', $LogLevel
  )
  Write-Host ("Starting HTTPS server on https://127.0.0.1:{0} (Uvicorn + TLS) ..." -f $Port) -ForegroundColor Green
  try {
    python @args
    return $LASTEXITCODE
  } catch {
    return 1
  }
}

function Start-DjangoRunserver {
  param([string]$ServerHost, [string]$ServerPort)
  $url = ("http://{0}:{1}" -f $ServerHost, $ServerPort)
  Write-Host "Starting plain HTTP dev server at $url ..." -ForegroundColor Yellow
  python backend\manage.py runserver ("{0}:{1}" -f $ServerHost, $ServerPort)
}

# ------------- Quick Health Check -------------
function Test-PythonAvailable {
  try {
    $null = Get-Command python -ErrorAction Stop
    return $true
  } catch {
    Write-Warning "Python not found on PATH. Ensure virtualenv is activated: .\\.venv\\Scripts\\Activate.ps1"
    return $false
  }
}
function Test-DjangoManage {
  try {
    python backend\manage.py --version | Out-Null
    return $true
  } catch {
    Write-Warning ("Django manage.py not runnable: {0}" -f $_.Exception.Message)
    return $false
  }
}
function Start-HealthCheck {
  param(
    [bool]$TlsExpected,
    [string]$KeyFile,
    [string]$CertFile,
    [int]$TlsPort
  )
  $ok = $true
  if (-not (Test-PythonAvailable)) { $ok = $false }
  if (-not (Test-DjangoManage))   { $ok = $false }
  if ($TlsExpected) {
    if (-not (Test-Path -Path $KeyFile)) { Write-Warning ("TLS key not found: {0}" -f $KeyFile); $ok = $false }
    if (-not (Test-Path -Path $CertFile)) { Write-Warning ("TLS cert not found: {0}" -f $CertFile); $ok = $false }
    try {
      $inUse = (Test-NetConnection -ComputerName '127.0.0.1' -Port $TlsPort -WarningAction SilentlyContinue).TcpTestSucceeded
      if ($inUse) { Write-Warning ("TLS port {0} already in use." -f $TlsPort) }
    } catch { }
  }
  return $ok
}

function Test-DjangoDbConnection {
  try {
    # Build a small Python probe that ensures backend/ is on sys.path, sets DJANGO_SETTINGS_MODULE,
    # calls django.setup(), and verifies DB connectivity via SELECT 1. Exits with code 0 on success.
    $BackendPath = Join-Path $Root 'backend'
    $BackendPathEsc = $BackendPath -replace '\\','\\'
    $code = @"
import os, sys
backend_path = r'$BackendPathEsc'
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)
# Ensure settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE','core.settings')
try:
    import django
    django.setup()
    from django.db import connection
    with connection.cursor() as c:
        c.execute('SELECT 1')
        c.fetchone()
    print('OK')
    raise SystemExit(0)
except Exception as e:
    # Do not spam full trace during PowerShell probe; non-zero exit code is enough
    raise SystemExit(1)
"@
    $tmp = New-TemporaryFile
    Set-Content -Path $tmp -Value $code -Encoding UTF8
    $output = & python $tmp 2>$null
    $exit = $LASTEXITCODE
    Remove-Item $tmp -ErrorAction SilentlyContinue
    if ($exit -eq 0 -and ($output -match 'OK')) { return $true } else { return $false }
  } catch {
    return $false
  }
}

# ------------- Preflight -------------
$DotEnv = Read-DotEnv -Path $EnvFile

# Ensure DEBUG=true by default in local dev if not explicitly set
if (-not $Env:DJANGO_DEBUG -or $Env:DJANGO_DEBUG -eq '') { $Env:DJANGO_DEBUG = 'true' }

# Probe DB connectivity; require PostgreSQL (no SQLite fallback)
if (-not (Test-DjangoDbConnection)) {
  Write-Error -Message "Failed to connect to PostgreSQL. Ensure PostgreSQL is running and PG_* settings are set in backend/.env, then retry."
  exit 1
}

Invoke-DjangoMigrateIfNeeded
Ensure-Superuser -DotEnv $DotEnv

# ------------- Certs -------------
New-DevCertificatesIfMissing -Key $KeyPath -Crt $CrtPath -GeneratorPath $MakeCert
$CanTryTls = (Test-Path -Path $KeyPath) -and (Test-Path -Path $CrtPath)

# ------------- Port / Logging -------------
$BaseTlsPort   = if ($Env:DJANGO_TLS_PORT) { [int]$Env:DJANGO_TLS_PORT } else { $DEFAULT_TLS_PORT }
$TlsPort       = Get-AvailableTlsPort -Preferred $BaseTlsPort -ProbeRange $TLS_PROBE_RANGE
$LogLevel      = if ($Env:DJANGO_UVICORN_LOG_LEVEL) { $Env:DJANGO_UVICORN_LOG_LEVEL } else { $DEFAULT_LOG_LEVEL }
$SuperuserName = if ($DotEnv -and $DotEnv['DJANGO_SUPERUSER_USERNAME']) { $DotEnv['DJANGO_SUPERUSER_USERNAME'] } else { 'mesuef' }

# Persist selected TLS port for other tools (e.g., dev_all.ps1) and display clear info
try {
  $RuntimeDir = Join-Path $Root 'backend\.runtime'
  if (-not (Test-Path -Path $RuntimeDir)) { New-Item -ItemType Directory -Force -Path $RuntimeDir | Out-Null }
  $PortFile = Join-Path $RuntimeDir 'https_port.txt'
  Set-Content -Path $PortFile -Value $TlsPort -Encoding ASCII
} catch { }

if ($TlsPort -ne $BaseTlsPort) {
  Write-Host ("Note: Preferred port {0} was busy; selected free port {1}." -f $BaseTlsPort, $TlsPort) -ForegroundColor DarkYellow
}
Write-Host ("Admin login URL: https://127.0.0.1:{0}/admin/  (user: {1})" -f $TlsPort, $SuperuserName) -ForegroundColor DarkGray

# ------------- Start Server -------------
if ($CanTryTls) {
  if (-not (Start-HealthCheck -TlsExpected $true -KeyFile $KeyPath -CertFile $CrtPath -TlsPort $TlsPort)) {
    Write-Host "Preflight checks failed; falling back to Django runserver (HTTP)." -ForegroundColor DarkYellow
  } else {
    $exitCode = Start-UvicornTls -Port $TlsPort -KeyFile $KeyPath -CertFile $CrtPath -LogLevel $LogLevel -App $UVICORN_APP -AppDir $UVICORN_APP_DIR
    if ($exitCode -eq 0) { exit 0 }
    Write-Warning ("Uvicorn HTTPS exited with code {0}. Falling back to Django runserver (HTTP)." -f $exitCode)
  }
} else {
  Write-Warning "TLS certs not available. Falling back to Django runserver (HTTP)."
}

$ServerHost = if ($Env:DJANGO_RUN_HOST) { $Env:DJANGO_RUN_HOST } else { $DEFAULT_HTTP_HOST }
$ServerPort = if ($Env:DJANGO_RUN_PORT) { $Env:DJANGO_RUN_PORT } else { $DEFAULT_HTTP_PORT }

if (-not (Start-HealthCheck -TlsExpected $false -KeyFile $null -CertFile $null -TlsPort 0)) {
  Write-Warning "Cannot start Django runserver due to failed preflight (Python/Django not ready)."
} else {
  Start-DjangoRunserver -ServerHost $ServerHost -ServerPort $ServerPort
}