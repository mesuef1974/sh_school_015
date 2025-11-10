#requires -Version 5.1
Param(
  [Parameter(Mandatory=$false)] [string]$BaseUrl = 'https://127.0.0.1:8443/api/v1',
  [Parameter(Mandatory=$false)] [string]$Token,
  [Parameter(Mandatory=$false)] [string]$TokenFile,
  [switch]$SkipCertificateCheck
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Write-Header($t){ Write-Host ("== {0} ==" -f $t) -ForegroundColor Cyan }
function Write-Note($t){ Write-Host $t -ForegroundColor DarkGray }

function Get-TokenFromFile([string]$path){
  try {
    if ($path -and (Test-Path -LiteralPath $path)) {
      $raw = Get-Content -LiteralPath $path -ErrorAction Stop | Select-Object -First 1
      if ($raw) { return ($raw.Trim()) }
    }
  } catch {}
  return ''
}

function Invoke-Api {
  param([string]$Path)
  $uri = ($BaseUrl.TrimEnd('/')) + $Path
  $headers = @{}
  if ($script:TokenEffective -and $script:TokenEffective -ne '') { $headers['Authorization'] = "Bearer $script:TokenEffective" }
  try {
    if ($SkipCertificateCheck) {
      $res = Invoke-WebRequest -Uri $uri -Method GET -Headers $headers -SkipCertificateCheck -TimeoutSec 6 -ErrorAction Stop
    } else {
      $res = Invoke-WebRequest -Uri $uri -Method GET -Headers $headers -TimeoutSec 6 -ErrorAction Stop
    }
    $json = $null
    try { $json = $res.Content | ConvertFrom-Json } catch { $json = $res.Content }
    return @{ ok=$true; status=$res.StatusCode; data=$json }
  } catch {
    $status = $_.Exception.Response.StatusCode.Value__ 2>$null
    $body = ''
    try { $sr = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream()); $body = $sr.ReadToEnd() } catch {}
    return @{ ok=$false; status=$status; error=$_.Exception.Message; body=$body }
  }
}

# Determine effective token: explicit -Token wins, then -TokenFile
$script:TokenEffective = ''
if ($Token -and $Token -ne '') { $script:TokenEffective = $Token }
elseif ($TokenFile -and $TokenFile -ne '') { $script:TokenEffective = Get-TokenFromFile $TokenFile }

Write-Header 'Discipline Incidents Smoke (Diagnostics)'
Write-Note ("BaseUrl: {0}" -f $BaseUrl)
if (-not $script:TokenEffective -or $script:TokenEffective -eq '') {
  Write-Host "No Bearer token provided. If you receive 401, you can:" -ForegroundColor Yellow
  Write-Host "  - Run: pwsh -File scripts/exec_hub.ps1 login:test (then copy the access token)" -ForegroundColor Yellow
  Write-Host "  - Rerun with: -Token <ACCESS_TOKEN>  OR save it to a file and use -TokenFile <PATH>" -ForegroundColor Yellow
}

Write-Header '1) Visible counts'
$vis = Invoke-Api '/discipline/incidents/visible/'
if (-not $vis.ok) {
  Write-Host ("FAILED ({0}) -> {1}" -f ($vis.status), $vis.error) -ForegroundColor Red
  if ($vis.status -eq 401) {
    Write-Host 'Unauthorized (401). Please obtain a JWT and pass -Token, or login in the frontend and retry.' -ForegroundColor Yellow
    if ($TokenFile -and -not (Test-Path -LiteralPath $TokenFile)) {
      Write-Note ("Tip: save your access token text into: {0} then rerun with -TokenFile '{0}'" -f $TokenFile)
    }
  }
} else {
  $mc = $vis.data.mine_count
  $ac = $vis.data.all_count
  $mineIds = $vis.data.sample.mine -join ','
  $allIds = $vis.data.sample.all -join ','
  Write-Host ("mine_count={0}, all_count={1}" -f $mc,$ac) -ForegroundColor Green
  Write-Host ("sample.mine=[{0}]" -f $mineIds) -ForegroundColor DarkGreen
  Write-Host ("sample.all=[{0}]" -f $allIds) -ForegroundColor DarkGreen
}

Write-Header '2) Incidents (ALL, first 5)'
$all = Invoke-Api '/discipline/incidents/?page_size=5'
if ($all.ok) { Write-Output ($all.data | ConvertTo-Json -Depth 6) } else { Write-Host ("FAILED ({0}) -> {1}" -f $all.status, $all.error) -ForegroundColor Red; if ($all.body) { Write-Output $all.body } }

Write-Header '3) Incidents (MINE, first 5)'
$mine = Invoke-Api '/discipline/incidents/?mine=1&page_size=5'
if ($mine.ok) { Write-Output ($mine.data | ConvertTo-Json -Depth 6) } else { Write-Host ("FAILED ({0}) -> {1}" -f $mine.status, $mine.error) -ForegroundColor Red; if ($mine.body) { Write-Output $mine.body } }

Write-Header 'Summary'
if ($vis.ok) {
  Write-Note 'If mine_count>0 but UI is empty on scope=mine, likely a frontend parsing/filters issue.'
  Write-Note 'If all_count>0 and UI on scope=all is empty for privileged users, check API params/status filter.'
  Write-Note 'If both are 0 but DB has records, check reporter assignments and status filters.'
} else {
  Write-Note 'visible/ failed. Fix auth (401) or backend errors, then rerun.'
}

# Exit non-zero on 401 or other error on the first critical endpoint
if (-not $vis.ok) { exit 1 } else { exit 0 }
