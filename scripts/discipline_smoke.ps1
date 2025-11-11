#requires -Version 5.1
Param(
  [Parameter(Mandatory=$false)] [string]$BaseUrl = 'https://127.0.0.1:8443/api/v1',
  [Parameter(Mandatory=$false)] [string]$Token,
  [switch]$SkipCertificateCheck
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Write-Header($t){ Write-Host ("== {0} ==" -f $t) -ForegroundColor Cyan }
function Write-Note($t){ Write-Host $t -ForegroundColor DarkGray }

function Invoke-Api {
  param([string]$Path)
  $uri = ($BaseUrl.TrimEnd('/')) + $Path
  $headers = @{}
  if ($Token -and $Token -ne '') { $headers['Authorization'] = "Bearer $Token" }
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

Write-Header 'Discipline Incidents Smoke (Diagnostics)'
Write-Note ("BaseUrl: {0}" -f $BaseUrl)
if (-not $Token -or $Token -eq '') {
  Write-Host "No Bearer token provided. If you receive 401, run: pwsh -File scripts/exec_hub.ps1 login:test and copy the access token, then rerun with -Token <ACCESS_TOKEN>." -ForegroundColor Yellow
}

Write-Header '1) Visible counts'
$vis = Invoke-Api '/discipline/incidents/visible/'
if (-not $vis.ok) {
  Write-Host ("FAILED ({0}) -> {1}" -f ($vis.status), $vis.error) -ForegroundColor Red
  if ($vis.status -eq 401) { Write-Host 'Unauthorized. Please obtain a JWT and pass -Token, or login in the frontend and retry.' -ForegroundColor Yellow }
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
