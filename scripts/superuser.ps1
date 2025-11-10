#requires -Version 5.1
<#!
Professional one-liner to create/ensure a Django superuser.

Usage examples:
  # Use defaults from backend/.env, or fallback username 'mesuef'
  pwsh -File scripts/superuser.ps1

  # Explicit username and email; generate a strong random password and print it
  pwsh -File scripts/superuser.ps1 -Username admin -Email admin@example.com -RandomPassword -PrintCredentials

  # Fully explicit (non-interactive)
  pwsh -File scripts/superuser.ps1 -Username admin -Email admin@example.com -Password "StrongP@ss!123"

Notes:
- This is a thin, user-friendly wrapper around scripts/ensure_superuser.ps1 which performs DB self-heal.
- Password can be provided in plain text here for local development convenience. Prefer -RandomPassword for quick secure setup.
!#>
[CmdletBinding()]
Param(
  [string]$Username,
  [string]$Email,
  [string]$Password,
  [switch]$RandomPassword,
  [switch]$PrintCredentials,
  [switch]$Quiet
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# Move to repo root
$Root = Resolve-Path (Join-Path $PSScriptRoot '..')
Set-Location $Root

# Activate venv if available
$VenvActivate = Join-Path $Root '.venv\Scripts\Activate.ps1'
if (Test-Path -LiteralPath $VenvActivate) { try { . $VenvActivate } catch { } }

# Ensure Python available (will be used by underlying script)
try { python --version *> $null } catch { Write-Error 'Python not found on PATH. Activate .venv first: .\.venv\Scripts\Activate.ps1'; exit 1 }

function Read-DotEnv {
  param([string]$Path)
  $result = @{}
  if (-not (Test-Path -Path $Path)) { return $result }
  try {
    Get-Content $Path | Where-Object { $_ -and ($_ -notmatch '^[\s#]') } | ForEach-Object {
      if ($_ -match '^(?<k>[^=\s]+)=(?<v>.*)$') { $result[$Matches['k'].Trim()] = $Matches['v'].Trim() }
    }
  } catch {}
  return $result
}
function ConvertFrom-QuotedValue([string]$s){ if (-not $s){return $s}; $t=$s.Trim(); if($t.Length -ge 2){$f=$t[0];$l=$t[$t.Length-1]; if(($f -eq '"' -and $l -eq '"') -or ($f -eq "'" -and $l -eq "'")){ return $t.Substring(1,$t.Length-2)} }; return $t }

# Load .env for sensible defaults
$EnvFile = Join-Path $Root 'backend\.env'
$DotEnv = Read-DotEnv -Path $EnvFile

# Derive username/email if not provided
if (-not $Username -or $Username.Trim() -eq '') { $Username = ($DotEnv['DJANGO_SUPERUSER_USERNAME']); if (-not $Username -or $Username.Trim() -eq '') { $Username = 'mesuef' } }
if (-not $Email -or $Email.Trim() -eq '') { $Email = ($DotEnv['DJANGO_SUPERUSER_EMAIL']) }

# Determine password
$generated = $false
if ($RandomPassword) {
  # Generate a strong 20-char password with mixed classes
  $len = 20
  $lower = 'abcdefghijklmnopqrstuvwxyz'
  $upper = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
  $digits = '0123456789'
  $symbols = '!@#$%^&*()-_=+[]{}:,<.>/?'
  $all = ($lower + $upper + $digits + $symbols)
  $rand = New-Object System.Random
  $chars = New-Object System.Collections.Generic.List[char]
  # Ensure at least one of each class
  $chars.Add($lower[$rand.Next(0,$lower.Length)])
  $chars.Add($upper[$rand.Next(0,$upper.Length)])
  $chars.Add($digits[$rand.Next(0,$digits.Length)])
  $chars.Add($symbols[$rand.Next(0,$symbols.Length)])
  for ($i=4; $i -lt $len; $i++) { $chars.Add($all[$rand.Next(0,$all.Length)]) }
  # Shuffle
  for ($i=0; $i -lt $chars.Count; $i++) { $j = $rand.Next(0,$chars.Count); $tmp=$chars[$i]; $chars[$i]=$chars[$j]; $chars[$j]=$tmp }
  $Password = -join $chars
  $generated = $true
} elseif (-not $Password -or $Password.Trim() -eq '') {
  # Fall back to .env password or leave empty to let underlying script pick defaults
  $Password = ConvertFrom-QuotedValue $DotEnv['DJANGO_SUPERUSER_PASSWORD']
}

# Export env vars for Django command to consume
$env:DJANGO_SUPERUSER_USERNAME = $Username
if ($Email)    { $env:DJANGO_SUPERUSER_EMAIL = $Email }
if ($Password) { $env:DJANGO_SUPERUSER_PASSWORD = $Password }

# Build args for underlying ensure_superuser.ps1
$ensureScript = Join-Path $Root 'scripts\ensure_superuser.ps1'
if (-not (Test-Path -LiteralPath $ensureScript)) { Write-Error "Required script not found: $ensureScript"; exit 1 }

$forwardArgs = @()
if ($Username) { $forwardArgs += @('--username', $Username) }

if (-not $Quiet) {
  Write-Host ("Ensuring superuser '{0}' ..." -f $Username) -ForegroundColor Cyan
  if ($Email) { Write-Host ("  Email: {0}" -f $Email) -ForegroundColor DarkGray }
}

# Invoke the robust ensure script (it will self-heal DB if needed)
& $ensureScript @forwardArgs
$code = $LASTEXITCODE
if ($code -ne 0) { exit $code }

# Optional: print credentials and admin URL hint
try {
  $runtimeDir = Join-Path $Root 'backend\.runtime'
  $httpsPortFile = Join-Path $runtimeDir 'https_port.txt'
  $port = 8443
  if (Test-Path -LiteralPath $httpsPortFile) {
    try { $pval = [int](Get-Content -Path $httpsPortFile | Select-Object -First 1); if ($pval) { $port = $pval } } catch {}
  }
  if ($PrintCredentials) {
    Write-Host ("Admin URL: https://127.0.0.1:{0}/admin/" -f $port) -ForegroundColor Green
    Write-Host ("Username: {0}" -f $Username) -ForegroundColor Green
    if ($Password) { Write-Host ("Password: {0}" -f $Password) -ForegroundColor Yellow }
  } else {
    Write-Host ("Admin URL: https://127.0.0.1:{0}/admin/" -f $port) -ForegroundColor DarkGray
    if ($generated) { Write-Host "A strong password was generated. Use -PrintCredentials to display it now." -ForegroundColor DarkGray }
  }
} catch { }

exit 0
