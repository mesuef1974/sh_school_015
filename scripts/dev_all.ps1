#requires -Version 5.1
Param(
  [switch]$ForceFrontend = $false,
  [int]$MaxWaitSeconds = 30
)
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

# Try to import shared ops utilities
$utils = Join-Path $Root 'scripts\lib\ops_utils.psm1'
if (Test-Path $utils) { try { Import-Module $utils -Force -ErrorAction Stop } catch {} }

# Wait for backend to be ready (best-effort) to reduce frontend proxy ECONNREFUSED
$backendReady = $false
# Discover selected backend origin/port written by serve_https.ps1
$originFile = Join-Path $Root 'backend\.runtime\dev_origin.txt'
$portFile = Join-Path $Root 'backend\.runtime\https_port.txt'
$scheme = 'https'
$backendHost = '127.0.0.1'
$port = 8443
$lastOrigin = $null
if (Test-Path -Path $originFile) {
  try {
    $originStr = (Get-Content -Path $originFile -ErrorAction Stop | Select-Object -First 1)
    if ($originStr) {
      $u = [Uri]$originStr
      $scheme = $u.Scheme
      $backendHost = $u.Host
      $port = $u.Port
    }
  } catch {}
} elseif (Test-Path -Path $portFile) {
  try { $port = [int]((Get-Content -Path $portFile -ErrorAction Stop | Select-Object -First 1)) } catch {}
}
function Get-ProbeUri {
  param([string]$Sch,[string]$H,[int]$P)
  return ("{0}://{1}:{2}/livez" -f $Sch,$H,$P)
}
$probeUri = Get-ProbeUri -Sch $scheme -H $backendHost -P $port
# Determine attempts from -MaxWaitSeconds with 500ms interval
$attempts = [math]::Ceiling(($MaxWaitSeconds * 1000) / 500)
for ($i = 0; $i -lt $attempts; $i++) {
  # Re-read origin selection on every iteration to follow serve_https dynamic choice
  if (Test-Path -Path $originFile) {
    try {
      $originStr = (Get-Content -Path $originFile -ErrorAction Stop | Select-Object -First 1)
      if ($originStr -and $originStr -ne $lastOrigin) {
        $u = [Uri]$originStr
        $scheme = $u.Scheme; $backendHost = $u.Host; $port = $u.Port
        $probeUri = Get-ProbeUri -Sch $scheme -H $backendHost -P $port
        $lastOrigin = $originStr
      }
    } catch {}
  } elseif (Test-Path -Path $portFile) {
    try {
      $candidate = [int]((Get-Content -Path $portFile -ErrorAction Stop | Select-Object -First 1))
      if ($candidate -and $candidate -ne $port) {
        $port = $candidate
        $probeUri = Get-ProbeUri -Sch 'https' -H $backendHost -P $port
      }
    } catch {}
  }
  if ($probeUri -ne $lastOrigin) {
    Write-Host ("Probing backend readiness at {0}" -f $probeUri) -ForegroundColor DarkGray
    $lastOrigin = $probeUri
  }
  try {
    $resp = Invoke-HttpGetCompat -Uri $probeUri -TimeoutSec 3 -Insecure:($scheme -eq 'https')
    if ($resp.StatusCode -eq 204 -or $resp.StatusCode -eq 200) { $backendReady = $true; break }
  } catch {}
  Start-Sleep -Milliseconds 500
}
if ($backendReady) {
  Write-Host 'Backend is up - starting frontend (Vite) ...' -ForegroundColor Cyan
} else {
  if (-not $ForceFrontend) {
    Write-Host 'Backend not confirmed yet - not starting frontend. Re-run with -ForceFrontend or increase -MaxWaitSeconds.' -ForegroundColor DarkYellow
    exit 1
  } else {
    Write-Host 'Backend not confirmed yet - starting frontend anyway due to -ForceFrontend.' -ForegroundColor DarkYellow
  }
}

# Start frontend Vite dev server
Write-Host 'Starting frontend (Vite dev server) ...' -ForegroundColor Cyan
Push-Location (Join-Path $Root 'frontend')
try {
  # Export backend origin/port for Vite proxy
  $env:VITE_BACKEND_PORT = "$port"
  $env:VITE_BACKEND_ORIGIN = ("{0}://{1}:{2}" -f $scheme, $backendHost, $port)
  Write-Host ("Vite will proxy to {0}" -f $env:VITE_BACKEND_ORIGIN) -ForegroundColor DarkGray
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

      # Ensure local Vite is available for vite.config.ts imports (with EBUSY/esbuild retry)
      $hasLocalVite = Test-Path 'node_modules\vite\package.json'
      if (-not $hasLocalVite) {
        Write-Host 'Installing Vite as a dev dependency (npm i -D vite) ...' -ForegroundColor Yellow
        try {
          npm install -D vite
          $hasLocalVite = Test-Path 'node_modules\vite\package.json'
        } catch {
          Write-Warning "First attempt to install Vite failed: $($_.Exception.Message)"
          # Try to unlock esbuild binary commonly held by AV/previous runs
          $esb = 'node_modules\@esbuild\win32-x64'
          if (Test-Path $esb) {
            Write-Host 'Cleaning up locked esbuild directory and retrying...' -ForegroundColor Yellow
            try { Remove-Item -LiteralPath $esb -Force -Recurse -ErrorAction SilentlyContinue } catch {}
          }
          try {
            npm install -D vite
            $hasLocalVite = Test-Path 'node_modules\vite\package.json'
          } catch {
            Write-Warning "Retry to install Vite failed. Will use NPX with a fallback config that does not import local 'vite'."
          }
        }
      }

      # Attempt to start via npm script; in PowerShell a non-zero exit code does not throw by default
      $global:LASTEXITCODE = 0
      npm run dev
      $npmExit = $LASTEXITCODE
      if ($npmExit -ne 0) {
        Write-Warning "npm run dev exited with code $npmExit. Trying 'npx vite' fallback..."
        try {
          if (-not $hasLocalVite -and (Test-Path 'vite.dev.fallback.mjs')) {
            npx --yes vite --config vite.dev.fallback.mjs
          } else {
            npx --yes vite
          }
        } catch {
          Write-Error "Failed to start Vite (npx). Please install dev dependency 'vite' (npm i -D vite) or add it to package.json scripts. Error: $($_.Exception.Message)"
          exit 1
        }
      }
    }
  } else {
    Write-Warning 'frontend/package.json not found.'
  }
} finally {
  Pop-Location
}
