#requires -Version 5.1
Param(
  [switch]$HttpsOnly,
  [int]$HttpPort = 8000
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# Move to repo root
$Root = Resolve-Path (Join-Path $PSScriptRoot '..')
Set-Location $Root

function Get-HttpsPort {
  $portFile = Join-Path $Root 'backend\.runtime\https_port.txt'
  $port = 8443
  if (Test-Path -Path $portFile) {
    try { $raw = Get-Content -Path $portFile -ErrorAction Stop | Select-Object -First 1; if ($raw) { $port = [int]$raw } } catch { }
  }
  return $port
}

function Test-Endpoint($Label, $Url, [switch]$SkipCert) {
  try {
    if ($SkipCert) {
      $resp = Invoke-WebRequest -Uri $Url -Method GET -SkipCertificateCheck -TimeoutSec 4 -ErrorAction Stop
    } else {
      $resp = Invoke-WebRequest -Uri $Url -Method GET -TimeoutSec 4 -ErrorAction Stop
    }
    Write-Host ("{0}: {1}" -f $Label, $resp.StatusCode) -ForegroundColor Green
  } catch {
    Write-Host ("{0}: FAILED - {1}" -f $Label, $_.Exception.Message) -ForegroundColor Red
  }
}

function Test-TcpOpen($TcpHost, [int]$Port, [int]$TimeoutMs = 800) {
  # Note: avoid using parameter name `$Host` which collides with PowerShell automatic variable `$Host` (read-only)
  try {
    $client = New-Object System.Net.Sockets.TcpClient
    $iar = $client.BeginConnect($TcpHost, $Port, $null, $null)
    $ok = $iar.AsyncWaitHandle.WaitOne($TimeoutMs, $false)
    $isOpen = $ok -and $client.Connected
    $client.Close()
    return $isOpen
  } catch {
    return $false
  }
}

Write-Host '== Attendance History Smoke Test ==' -ForegroundColor Cyan

# HTTPS endpoints
$httpsPort = Get-HttpsPort
$livez = "https://127.0.0.1:{0}/livez" -f $httpsPort
$healthz = "https://127.0.0.1:{0}/healthz" -f $httpsPort
Test-Endpoint "HTTPS /livez" $livez -SkipCert
Test-Endpoint "HTTPS /healthz" $healthz -SkipCert

# Dump URL patterns for diagnostics (DEBUG only endpoint)
$urlsDump = "https://127.0.0.1:{0}/api/v1/__urls__" -f $httpsPort
try {
  $dump = Invoke-WebRequest -Uri $urlsDump -Method GET -SkipCertificateCheck -TimeoutSec 4 -ErrorAction Stop | Select-Object -Expand Content
  Write-Host "-- URL dump (first 20 lines) --" -ForegroundColor DarkGray
  $lines = $dump -split "`n"
  $preview = $lines | Select-Object -First 20
  $preview | ForEach-Object { Write-Host $_ -ForegroundColor DarkGray }
} catch {
  Write-Host ("Could not fetch __urls__ dump: {0}" -f $_.Exception.Message) -ForegroundColor DarkYellow
}

# Unauthenticated should yield 401
$histUrl = "https://127.0.0.1:{0}/api/v1/attendance/history/?class_id=1" -f $httpsPort
try {
  Invoke-WebRequest -Uri $histUrl -Method GET -SkipCertificateCheck -TimeoutSec 4 -ErrorAction Stop | Out-Null
  Write-Host 'HTTPS /attendance/history (no token): UNEXPECTED SUCCESS (should be 401)' -ForegroundColor Yellow
} catch {
  try { $status = $_.Exception.Response.StatusCode.value__ } catch { $status = $null }
  if ($status -eq 401) { Write-Host 'HTTPS /attendance/history (no token): 401 (expected)' -ForegroundColor Green }
  else { Write-Host ("HTTPS /attendance/history (no token): FAILED - {0}" -f $_.Exception.Message) -ForegroundColor DarkYellow }
}


if (-not $HttpsOnly) {
  # Optional HTTP checks: only attempt if port 8000 is listening
  $httpPort = 8000
  if (-not (Test-TcpOpen '127.0.0.1' $httpPort)) {
    Write-Host ("HTTP checks: skipped (port {0} closed or not exposed in this environment)" -f $httpPort) -ForegroundColor DarkYellow
  } else {
    try {
      Invoke-WebRequest -Uri 'http://127.0.0.1:8000/healthz' -Method GET -TimeoutSec 3 -ErrorAction Stop | Out-Null
      Write-Host 'HTTP /healthz: 200' -ForegroundColor Green
    } catch {
      Write-Host ("HTTP /healthz: FAILED - {0}" -f $_.Exception.Message) -ForegroundColor DarkYellow
    }
    try {
      Invoke-WebRequest -Uri 'http://127.0.0.1:8000/api/v1/attendance/history/?class_id=1' -Method GET -TimeoutSec 3 -ErrorAction Stop | Out-Null
      Write-Host 'HTTP /attendance/history (no token): UNEXPECTED SUCCESS (should be 401)' -ForegroundColor Yellow
    } catch {
      try { $status2 = $_.Exception.Response.StatusCode.value__ } catch { $status2 = $null }
      if ($status2 -eq 401) { Write-Host 'HTTP /attendance/history (no token): 401 (expected)' -ForegroundColor Green }
      else { Write-Host ("HTTP /attendance/history (no token): FAILED - {0}" -f $_.Exception.Message) -ForegroundColor DarkYellow }
    }
  }
}

Write-Host 'History smoke test finished.' -ForegroundColor Cyan