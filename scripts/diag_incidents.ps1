#requires -Version 5.1
Param(
  [string]$BaseUrl = 'https://127.0.0.1:8443',
  [string]$WingId = '',
  [string]$From = '',
  [string]$To = '',
  [switch]$IncludeOverview
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function New-Query {
  param([string]$WingId,[string]$From,[string]$To)
  $qs = @{}
  if ($WingId) { $qs['wing_id'] = $WingId }
  if ($From) { $qs['from'] = $From }
  if ($To) { $qs['to'] = $To }
  if ($qs.Count -eq 0) { return '' }
  $pairs = @()
  foreach ($kv in $qs.GetEnumerator()) {
    $k = [uri]::EscapeDataString([string]$kv.Key)
    $v = [uri]::EscapeDataString([string]$kv.Value)
    $pairs += ("{0}={1}" -f $k, $v)
  }
  if ($pairs.Count -eq 0) { return '' }
  return '?' + ($pairs -join '&')
}

$qs = New-Query -WingId $WingId -From $From -To $To

$outDir = Join-Path (Join-Path $PSScriptRoot '..') 'backend\.runtime\diag'
New-Item -ItemType Directory -Force -Path $outDir | Out-Null

Write-Host "Calling diagnostics endpoints at $BaseUrl ..." -ForegroundColor Cyan

function Save-Json {
  param([string]$Url,[string]$Path)
  try {
    # -SkipCertificateCheck works in PowerShell 7; in Windows PowerShell we fallback to Invoke-WebRequest
    $resp = $null
    try { $resp = Invoke-RestMethod -Method Get -Uri $Url -SkipCertificateCheck -TimeoutSec 10 -ErrorAction Stop } catch {
      $resp = Invoke-RestMethod -Method Get -Uri $Url -TimeoutSec 10 -ErrorAction Stop
    }
    $json = ($resp | ConvertTo-Json -Depth 10)
    Set-Content -LiteralPath $Path -Value $json -Encoding UTF8
    Write-Host "Saved => $Path" -ForegroundColor Green
  } catch {
    Write-Warning "Failed $Url : $($_.Exception.Message)"
  }
}

Save-Json -Url ("{0}/api/v1/discipline/incidents/admin-export/{1}" -f $BaseUrl,$qs) -Path (Join-Path $outDir 'admin_export.json')
Save-Json -Url ("{0}/api/v1/discipline/incidents/visible/{1}" -f $BaseUrl,$qs) -Path (Join-Path $outDir 'visible.json')
Save-Json -Url ("{0}/api/v1/discipline/incidents/summary/{1}" -f $BaseUrl,$qs) -Path (Join-Path $outDir 'summary.json')
Save-Json -Url ("{0}/api/v1/discipline/incidents/diagnostics/{1}" -f $BaseUrl,$qs) -Path (Join-Path $outDir 'diagnostics.json')

if ($IncludeOverview) {
  # نظرة عامة اختيارية لمدد 7 أيام (افتراضي). يمكن تعديلها لاحقًا لدعم days=30 إذا لزم.
  Save-Json -Url ("{0}/api/v1/discipline/incidents/overview/?days=7" -f $BaseUrl) -Path (Join-Path $outDir 'overview_7d.json')
}

Write-Host "Done. Check files under: $outDir" -ForegroundColor Cyan
