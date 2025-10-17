#requires -Version 5.1
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# Monorepo root
$Root = Resolve-Path (Join-Path $PSScriptRoot '..')
Set-Location $Root

# Ensure venv is activated if available
$VenvActivate = Join-Path $Root '.venv\Scripts\Activate.ps1'
if (Test-Path -Path $VenvActivate) { try { . $VenvActivate } catch { } }

# Ensure DEBUG for dev
if (-not $Env:DJANGO_DEBUG -or $Env:DJANGO_DEBUG -eq '') { $Env:DJANGO_DEBUG = 'true' }

Write-Host 'Starting backend (serve_https.ps1) in a new window...' -ForegroundColor Cyan
$serveScript = Join-Path $Root 'scripts\serve_https.ps1'
# Prefer PowerShell 7 (pwsh) if available; fall back to Windows PowerShell
$shellExe = 'powershell'
try { if (Get-Command pwsh -ErrorAction Stop) { $shellExe = 'pwsh' } } catch { $shellExe = 'powershell' }
Start-Process -FilePath $shellExe -ArgumentList @('-NoProfile','-NoExit','-ExecutionPolicy','Bypass','-File', $serveScript)

# Reduce fixed delay; readiness probe below will wait if needed
Start-Sleep -Milliseconds 500

# Wait for backend to be ready (best-effort) to reduce frontend proxy ECONNREFUSED
$backendReady = $false
# Discover selected backend HTTPS port if available
$portFile = Join-Path $Root 'backend\.runtime\https_port.txt'
$port = 8443
if (Test-Path -Path $portFile) {
  try { $port = [int]((Get-Content -Path $portFile -ErrorAction Stop | Select-Object -First 1)) } catch {}
}
$origin = ("https://127.0.0.1:{0}/livez" -f $port)
for ($i = 0; $i -lt 20; $i++) {
  try {
    # PowerShell 7: -SkipCertificateCheck to accept self-signed dev cert
    $resp = Invoke-WebRequest -Uri $origin -Method GET -SkipCertificateCheck -TimeoutSec 2 -ErrorAction Stop
    if ($resp.StatusCode -eq 204 -or $resp.StatusCode -eq 200) { $backendReady = $true; break }
  } catch {}
  Start-Sleep -Milliseconds 500
}
if ($backendReady) {
  Write-Host 'Backend is up - starting frontend (Vite) ...' -ForegroundColor Cyan
} else {
  Write-Host 'Backend not confirmed yet - starting frontend anyway.' -ForegroundColor DarkYellow
}

# Start frontend Vite dev server
Write-Host 'Starting frontend (Vite dev server) ...' -ForegroundColor Cyan
Push-Location (Join-Path $Root 'frontend')
try {
  if (Test-Path package.json) {
    if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
      Write-Warning 'npm is not available on PATH. Install Node.js to run the frontend dev server.'
    } else {
      # Ensure dependencies are installed at first run or when critical packages are missing
      $needsInstall = $false
      if (-not (Test-Path 'node_modules')) { $needsInstall = $true }
      if (-not $needsInstall -and -not (Test-Path 'node_modules\@tanstack\vue-query')) { $needsInstall = $true }
      if (-not $needsInstall -and -not (Test-Path 'node_modules\vue-toastification')) { $needsInstall = $true }
      if ($needsInstall) {
        Write-Host 'Installing frontend dependencies (npm install) ...' -ForegroundColor Yellow
        npm install
      }
      npm run dev
    }
  } else {
    Write-Warning 'frontend/package.json not found.'
  }
} finally {
  Pop-Location
}