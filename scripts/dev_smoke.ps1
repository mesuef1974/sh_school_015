#requires -Version 5.1
Param(
  [switch]$HttpsOnly
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
      $resp = Invoke-WebRequest -Uri $Url -Method GET -SkipCertificateCheck -TimeoutSec 3 -ErrorAction Stop
    } else {
      $resp = Invoke-WebRequest -Uri $Url -Method GET -TimeoutSec 3 -ErrorAction Stop
    }
    Write-Host ("{0}: {1}" -f $Label, $resp.StatusCode) -ForegroundColor Green
  } catch {
    Write-Host ("{0}: FAILED - {1}" -f $Label, $_.Exception.Message) -ForegroundColor Red
  }
}

Write-Host '== Quick smoke test ==' -ForegroundColor Cyan

# 1) HTTPS livez/healthz
$httpsPort = Get-HttpsPort
$livez = "https://127.0.0.1:{0}/livez" -f $httpsPort
$healthz = "https://127.0.0.1:{0}/healthz" -f $httpsPort
Test-Endpoint "HTTPS /livez" $livez -SkipCert
Test-Endpoint "HTTPS /healthz" $healthz -SkipCert

if (-not $HttpsOnly) {
  # 2) HTTP healthz if backend exposes it (may be disabled)
  Test-Endpoint "HTTP /healthz" 'http://127.0.0.1:8000/healthz'
}

# 3) API 401 checks (attendance endpoints) - expect 401 without token
$httpsApi401 = "https://127.0.0.1:{0}/api/v1/attendance/records/?class_id=1" -f $httpsPort
try {
  Invoke-WebRequest -Uri $httpsApi401 -Method GET -SkipCertificateCheck -TimeoutSec 3 -ErrorAction Stop | Out-Null
  Write-Host 'HTTPS API /attendance/records: UNEXPECTED SUCCESS (should be 401 without token)' -ForegroundColor Yellow
} catch {
  $status = $_.Exception.Response.StatusCode.value__
  if ($status -eq 401) { Write-Host 'HTTPS API /attendance/records: 401 (expected)' -ForegroundColor Green }
  else { Write-Host ("HTTPS API /attendance/records: FAILED - {0}" -f $_.Exception.Message) -ForegroundColor Red }
}

if (-not $HttpsOnly) {
  try {
    Invoke-WebRequest -Uri 'http://127.0.0.1:8000/api/v1/attendance/records/?class_id=1' -Method GET -TimeoutSec 3 -ErrorAction Stop | Out-Null
    Write-Host 'HTTP API /attendance/records: UNEXPECTED SUCCESS (should be 401 without token)' -ForegroundColor Yellow
  } catch {
    $status = $_.Exception.Response.StatusCode.value__
    if ($status -eq 401) { Write-Host 'HTTP API /attendance/records: 401 (expected)' -ForegroundColor Green }
    else { Write-Host ("HTTP API /attendance/records: FAILED - {0}" -f $_.Exception.Message) -ForegroundColor DarkYellow }
  }
}

Write-Host 'Smoke test finished.' -ForegroundColor Cyan