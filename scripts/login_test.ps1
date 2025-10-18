#requires -Version 5.1
Param(
  [Parameter(Mandatory=$false)] [string]$Username,
  [Parameter(Mandatory=$false)] [string]$Password,
  [Parameter(Mandatory=$false)] [string]$BaseUrl,
  [switch]$SkipCertificateCheck
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

function Write-Header($t){ Write-Host ("== {0} ==" -f $t) -ForegroundColor Cyan }
function Ok($t){ Write-Host ("[OK] {0}" -f $t) -ForegroundColor Green }
function Warn($t){ Write-Host ("[WARN] {0}" -f $t) -ForegroundColor DarkYellow }
function Fail($t){ Write-Host ("[FAIL] {0}" -f $t) -ForegroundColor Red }

# Determine base URL (default to local HTTPS dev server)
if (-not $BaseUrl -or $BaseUrl.Trim() -eq '') {
  $port = Get-HttpsPort
  $BaseUrl = "https://127.0.0.1:$port"
}
# Normalize BaseUrl: ensure scheme present, remove trailing slashes
function Normalize-BaseUrl([string]$u) {
  if (-not $u) { return $u }
  $u = $u.Trim()
  # If missing scheme, assume https
  if ($u -notmatch '^(?i)https?://') { $u = "https://$u" }
  # Remove any trailing slash(es)
  while ($u.Length -gt 0 -and $u.EndsWith('/')) { $u = $u.Substring(0, $u.Length - 1) }
  return $u
}
$BaseUrl = Normalize-BaseUrl $BaseUrl

Write-Header "JWT Login Test"
Write-Host ("Base URL: {0}" -f $BaseUrl) -ForegroundColor DarkGray

# Quick liveliness check on /livez (helps catch wrong port/URL early)
try {
  $livezUrl = "$BaseUrl/livez"
  if ($SkipCertificateCheck) {
    $lresp = Invoke-WebRequest -Uri $livezUrl -Method GET -SkipCertificateCheck -TimeoutSec 3 -ErrorAction Stop
  } else {
    $lresp = Invoke-WebRequest -Uri $livezUrl -Method GET -TimeoutSec 3 -ErrorAction Stop
  }
  # Accept 204 or 200
  if ($lresp.StatusCode -ne 204 -and $lresp.StatusCode -ne 200) {
    Write-Host ("[WARN] /livez returned {0}" -f $lresp.StatusCode) -ForegroundColor DarkYellow
  }
} catch {
  Write-Host ("[FAIL] Cannot reach {0} (livez): {1}" -f $livezUrl, $_.Exception.Message) -ForegroundColor Red
  exit 3
}

# Prepare a shared web session to persist cookies (HttpOnly refresh)
$session = New-Object Microsoft.PowerShell.Commands.WebRequestSession

# Helper to perform JSON POST with optional SkipCertificateCheck
function Invoke-PostJson {
  param(
    [string]$Url,
    [hashtable]$Body
  )
  $json = ($Body | ConvertTo-Json -Depth 5)
  if ($SkipCertificateCheck) {
    return Invoke-WebRequest -Uri $Url -Method POST -ContentType 'application/json' -Body $json -WebSession $session -SkipCertificateCheck -UseBasicParsing
  } else {
    return Invoke-WebRequest -Uri $Url -Method POST -ContentType 'application/json' -Body $json -WebSession $session -UseBasicParsing
  }
}

function Invoke-Get {
  param([string]$Url, [hashtable]$Headers)
  if ($SkipCertificateCheck) {
    return Invoke-WebRequest -Uri $Url -Method GET -Headers $Headers -WebSession $session -SkipCertificateCheck -UseBasicParsing
  } else {
    return Invoke-WebRequest -Uri $Url -Method GET -Headers $Headers -WebSession $session -UseBasicParsing
  }
}

# Prompt for credentials if not provided
if (-not $Username) { $Username = Read-Host 'Username' }
if (-not $Password) { $Password = Read-Host -AsSecureString 'Password' | ForEach-Object { [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($_)) } }

$success_obtain = $false
$success_me = $false
$success_refresh = $false
$access = $null

# 1) Obtain token
try {
  $resp = Invoke-PostJson -Url ("{0}/api/token/" -f $BaseUrl) -Body @{ username=$Username; password=$Password }
  $json = $resp.Content | ConvertFrom-Json
  if ($json.access) {
    $access = [string]$json.access
    Ok "Token obtain (/api/token/)"
    # Show if refresh cookie was set
    $cookieName = 'refresh_token'
    $cookie = $session.Cookies.GetCookies($BaseUrl) | Where-Object { $_.Name -eq $cookieName } | Select-Object -First 1
    if ($cookie) { Write-Host ("Cookie set: {0}; HttpOnly={1}; Expires={2}" -f $cookie.Name,$cookie.HttpOnly,$cookie.Expires) -ForegroundColor DarkGray }
    $success_obtain = $true
  } else {
    Fail "Token obtain did not return access"
  }
} catch {
  Fail ("Token obtain failed: {0}" -f $_.Exception.Message)
}

# 2) Call /api/me with Authorization header
if ($access) {
  try {
    $headers = @{ Authorization = "Bearer $access" }
    $resp2 = Invoke-Get -Url ("{0}/api/me/" -f $BaseUrl) -Headers $headers
    if ($resp2.StatusCode -eq 200) {
      Ok "/api/me reachable with access"
      $success_me = $true
    } else {
      Warn ("/api/me returned {0}" -f $resp2.StatusCode)
    }
  } catch {
    Fail ("/api/me failed: {0}" -f $_.Exception.Message)
  }
}

# 3) Refresh access (prefer HttpOnly cookie)
try {
  $resp3 = Invoke-PostJson -Url ("{0}/api/token/refresh/" -f $BaseUrl) -Body @{}
  $json3 = $resp3.Content | ConvertFrom-Json
  if ($json3.access) {
    Ok "Token refresh (/api/token/refresh/)"
    $success_refresh = $true
  } else {
    Warn "Refresh returned no access (check cookie settings)"
  }
} catch {
  Warn ("Token refresh failed: {0}" -f $_.Exception.Message)
}

# Summary
Write-Host "`n== Summary ==" -ForegroundColor Cyan
if ($success_obtain) { Ok 'Obtain' } else { Fail 'Obtain' }
if ($success_me) { Ok 'ME' } else { Warn 'ME' }
if ($success_refresh) { Ok 'Refresh' } else { Warn 'Refresh' }

# Exit code: 0 if obtain succeeded, non-zero otherwise
if ($success_obtain) { exit 0 } else { exit 2 }