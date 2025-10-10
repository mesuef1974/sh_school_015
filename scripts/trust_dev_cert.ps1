#requires -Version 5.1
Param(
  [switch]$Machine,      # import into LocalMachine store (requires Admin)
  [switch]$Untrust       # remove previously trusted cert by thumbprint match
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# Move to project root
$Root = Resolve-Path (Join-Path $PSScriptRoot '..')
Set-Location $Root

$CertDir = Join-Path $Root 'backend\certs'
$CrtPath = Join-Path $CertDir 'dev.crt'

Write-Host '== Trust Dev Certificate ==' -ForegroundColor Cyan

if (-not (Test-Path -Path $CrtPath)) {
  Write-Warning "Certificate file not found: $CrtPath"
  Write-Host "Attempting to generate using scripts\\make_dev_cert.ps1 ..." -ForegroundColor DarkGray
  $make = Join-Path $Root 'scripts\make_dev_cert.ps1'
  if (Test-Path -Path $make) { & pwsh -NoProfile -ExecutionPolicy Bypass -File $make } else { Write-Error "Helper not found: $make" }
}

if (-not (Test-Path -Path $CrtPath)) { Write-Error "Certificate still not found at $CrtPath"; exit 1 }

# Load cert and compute thumbprint (compatible with PowerShell 7 / .NET where Import() is restricted)
try {
  # Detect PEM format quickly by header, otherwise assume DER/PKCS12 readable by constructor
  $firstLine = (Get-Content -Path $CrtPath -TotalCount 1 -ErrorAction Stop)
  $cert = $null
  if ($firstLine -match '-----BEGIN CERTIFICATE-----') {
    try {
      # Primary path (fast): .NET helper
      $cert = [System.Security.Cryptography.X509Certificates.X509Certificate2]::CreateFromPemFile($CrtPath)
    } catch {
      # Fallback: manually parse PEM and construct from DER bytes
      $raw = Get-Content -Path $CrtPath -Raw -ErrorAction Stop
      if ($raw -match '-----BEGIN CERTIFICATE-----([\s\S]*?)-----END CERTIFICATE-----') {
        $b64 = $Matches[1] -replace '\s',''
        $bytes = [Convert]::FromBase64String($b64)
        # Ensure the byte array is passed as a single constructor argument (avoid arg-splatting)
        $bytes = [byte[]]$bytes
        $cert  = [System.Security.Cryptography.X509Certificates.X509Certificate2]::new($bytes)
      } else {
        throw "Could not locate a CERTIFICATE PEM block in $CrtPath"
      }
    }
  } else {
    # Non-PEM files (DER/CRT/cer) should work with the constructor directly
    $cert = New-Object System.Security.Cryptography.X509Certificates.X509Certificate2($CrtPath)
  }
  $thumb = $cert.Thumbprint
  Write-Host ("Loaded cert: Subject='{0}', Thumbprint={1}" -f $cert.Subject, $thumb) -ForegroundColor DarkGray
} catch { Write-Error $_ }

# Target store
$storePath = if ($Machine) { 'Cert:\LocalMachine\Root' } else { 'Cert:\CurrentUser\Root' }

if ($Untrust) {
  Write-Host ("Removing cert with thumbprint {0} from {1} ..." -f $thumb, $storePath) -ForegroundColor Yellow
  try {
    $store = New-Object System.Security.Cryptography.X509Certificates.X509Store('Root', $(if ($Machine) {'LocalMachine'} else {'CurrentUser'}))
    $store.Open([System.Security.Cryptography.X509Certificates.OpenFlags]::ReadWrite)
    $toRemove = $store.Certificates | Where-Object { $_.Thumbprint -ieq $thumb }
    if ($toRemove) { $store.Remove($toRemove[0]); Write-Host 'Removed.' -ForegroundColor Green } else { Write-Host 'Certificate not found in store.' -ForegroundColor DarkGray }
    $store.Close()
    exit 0
  } catch {
    Write-Error $_; exit 2
  }
}

# Trust (import) into store
Write-Host ("Importing {0} into {1} ..." -f $CrtPath, $storePath) -ForegroundColor Green
try {
  $res = Import-Certificate -FilePath $CrtPath -CertStoreLocation $storePath -ErrorAction Stop
  if ($res) {
    Write-Host 'Trusted successfully.' -ForegroundColor Green
    Write-Host ("Thumbprint: {0}" -f $thumb)
    Write-Host 'Note: For LocalMachine store you must run PowerShell as Administrator.' -ForegroundColor DarkGray
    exit 0
  } else {
    Write-Warning 'Import-Certificate returned no result.'; exit 3
  }
} catch {
  Write-Error $_; exit 4
}