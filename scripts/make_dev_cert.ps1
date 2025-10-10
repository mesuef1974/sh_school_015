#requires -Version 5.1
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# Move to project root
$Root = Resolve-Path (Join-Path $PSScriptRoot '..')
Set-Location $Root

$CertDir = Join-Path $Root 'backend\certs'
New-Item -ItemType Directory -Force -Path $CertDir | Out-Null
$KeyPath = Join-Path $CertDir 'dev.key'
$CrtPath = Join-Path $CertDir 'dev.crt'

function Have-OpenSsl {
  $exe = Get-Command openssl -ErrorAction SilentlyContinue
  return $null -ne $exe
}

if ((Test-Path -Path $KeyPath) -and (Test-Path -Path $CrtPath)) {
  Write-Host "Certificates already exist:" -ForegroundColor Yellow
  Write-Host "  $KeyPath"
  Write-Host "  $CrtPath"
  exit 0
}

if (Have-OpenSsl) {
  Write-Host "Generating self-signed cert with OpenSSL..." -ForegroundColor Cyan

  # Ensure OpenSSL has a config file (some Windows installs require OPENSSL_CONF)
  $OpenSsl = Get-Command openssl -ErrorAction SilentlyContinue
  $OpenSslDir = if ($OpenSsl) { Split-Path -Parent $OpenSsl.Source } else { $null }
  $ConfCandidates = @()
  if ($OpenSslDir) {
    $parent = Split-Path -Parent $OpenSslDir
    $ConfCandidates += (Join-Path $parent 'ssl\openssl.cnf')
    $ConfCandidates += (Join-Path $parent 'usr\ssl\openssl.cnf')  # Git for Windows
    $ConfCandidates += (Join-Path $OpenSslDir 'ssl\openssl.cnf')
  }
  $ConfPath = $null
  foreach ($c in $ConfCandidates) {
    if (Test-Path -Path $c) { $ConfPath = (Resolve-Path $c).Path; break }
  }
  if (-not $ConfPath) {
    # Create a minimal config to satisfy OpenSSL on systems without a default openssl.cnf
    $ConfPath = Join-Path $CertDir 'openssl_dev.cnf'
    @"
[ req ]
distinguished_name = req_distinguished_name
prompt = no
[ req_distinguished_name ]
CN = localhost
"@ | Out-File -FilePath $ConfPath -Encoding ascii -Force
  }
  $env:OPENSSL_CONF = $ConfPath

  $args = @(
    'req','-x509','-nodes','-days','825','-newkey','rsa:2048',
    '-keyout', $KeyPath,
    '-out', $CrtPath,
    '-subj','/CN=localhost',
    '-addext','subjectAltName=DNS:localhost,IP:127.0.0.1'
  )
  & openssl @args | Out-Null
  if (!(Test-Path -Path $KeyPath) -or !(Test-Path -Path $CrtPath)) {
    throw "Failed to generate certificate files."
  }
  Write-Host "Done. Files ready:" -ForegroundColor Green
  Write-Host "  $KeyPath"
  Write-Host "  $CrtPath"
  Write-Host "Use with:" -ForegroundColor Green
  Write-Host "  python backend\manage.py runserver_plus --cert-file backend\certs\dev.crt --key-file backend\certs\dev.key 0.0.0.0:8443"
  Write-Host "  python -m uvicorn backend.core.asgi:application --host 0.0.0.0 --port 8443 --ssl-keyfile backend\certs\dev.key --ssl-certfile backend\certs\dev.crt"
  exit 0
}
else {
  Write-Warning "OpenSSL not found on PATH. Install Git for Windows (includes openssl.exe) or use Uvicorn without TLS."
  Write-Host "Alternatively, install mkcert or generate a cert via other tools and place files at:" -ForegroundColor Yellow
  Write-Host "  $KeyPath"
  Write-Host "  $CrtPath"
  exit 1
}