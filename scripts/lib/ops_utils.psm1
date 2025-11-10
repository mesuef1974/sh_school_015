# Common helpers for ops scripts (PowerShell 5.1+ and 7+ compatible)
Set-StrictMode -Version Latest

function Write-Ok($msg){ Write-Host "[OK] $msg" -ForegroundColor Green }
function Write-Err($msg){ Write-Host "[ERR] $msg" -ForegroundColor Red }
function Write-Info($msg){ Write-Host "[INFO] $msg" -ForegroundColor DarkGray }
function Write-Warn($msg){ Write-Host "[WARN] $msg" -ForegroundColor Yellow }

# Test if a TCP port is in use on localhost
function Test-PortBusy([int]$Port){
  try {
    return [bool](Test-NetConnection -ComputerName 127.0.0.1 -Port $Port -InformationLevel Quiet -WarningAction SilentlyContinue -ErrorAction SilentlyContinue)
  } catch { return $false }
}

# Find first free port starting from StartPort
function Find-FreePort([int]$StartPort, [int]$MaxTries = 50){
  $p = [int]$StartPort
  for ($i = 0; $i -lt $MaxTries; $i++) { if (-not (Test-PortBusy -Port $p)) { return $p }; $p++ }
  return [int]$StartPort
}

# Prefer PowerShell 7 (pwsh) if available; fall back to Windows PowerShell
function Get-PreferredShell {
  try { if (Get-Command pwsh -ErrorAction Stop) { return 'pwsh' } } catch {}
  return 'powershell'
}

# Read backend origin from runtime files produced by serve_https.ps1
function Read-BackendOrigin([string]$Root){
  $originFile = Join-Path $Root 'backend\.runtime\dev_origin.txt'
  $portFile = Join-Path $Root 'backend\.runtime\https_port.txt'
  $scheme = 'https'; $host = '127.0.0.1'; $port = 8443
  if (Test-Path $originFile) {
    try {
      $line = (Get-Content -Path $originFile -ErrorAction Stop | Select-Object -First 1)
      if ($line) { $u = [Uri]$line; $scheme = $u.Scheme; $host = $u.Host; $port = $u.Port }
    } catch {}
  } elseif (Test-Path $portFile) {
    try { $p = (Get-Content -Path $portFile -ErrorAction Stop | Select-Object -First 1); if ($p) { $port = [int]$p } } catch {}
  }
  [pscustomobject]@{ Scheme=$scheme; Host=$host; Port=$port; Origin=("{0}://{1}:{2}" -f $scheme,$host,$port) }
}

# HTTP GET that works on both PowerShell 5.1 and 7+, with optional TLS bypass.
function Invoke-HttpGetCompat {
  param(
    [Parameter(Mandatory=$true)][string]$Uri,
    [int]$TimeoutSec = 3,
    [switch]$Insecure
  )
  if ($PSVersionTable.PSVersion.Major -ge 6) {
    if ($Insecure) {
      return Invoke-WebRequest -Uri $Uri -Method GET -SkipCertificateCheck -TimeoutSec $TimeoutSec -ErrorAction Stop
    } else {
      return Invoke-WebRequest -Uri $Uri -Method GET -TimeoutSec $TimeoutSec -ErrorAction Stop
    }
  } else {
    $orig = [System.Net.ServicePointManager]::ServerCertificateValidationCallback
    if ($Insecure) { [System.Net.ServicePointManager]::ServerCertificateValidationCallback = { $true } }
    try {
      return Invoke-WebRequest -Uri $Uri -Method GET -TimeoutSec $TimeoutSec -ErrorAction Stop
    } finally {
      [System.Net.ServicePointManager]::ServerCertificateValidationCallback = $orig
    }
  }
}

Export-ModuleMember -Function Write-Ok,Write-Err,Write-Info,Write-Warn,Test-PortBusy,Find-FreePort,Get-PreferredShell,Read-BackendOrigin,Invoke-HttpGetCompat
