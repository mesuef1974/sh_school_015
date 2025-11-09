#requires -Version 5.1
<#
.SYNOPSIS
  Unified execution hub for common development tasks.

.DESCRIPTION
  Provides a curated set of safe, developer-focused commands with guardrails:
  - Dry-run via -WhatIf (simulation only)
  - Confirmation via -Confirm for risky tasks
  - DEV-only by default (blocks on PROD unless -Force specified; -Force not implemented yet for safety)

.EXAMPLES
  pwsh -File scripts/exec_hub.ps1 -List
  pwsh -File scripts/exec_hub.ps1 dev:up
  pwsh -File scripts/exec_hub.ps1 dev:up -WhatIf
  pwsh -File scripts/exec_hub.ps1 worker:start
  pwsh -File scripts/exec_hub.ps1 audit:full

.NOTES
  This script wraps existing repo scripts without altering them.
#>

Param(
  [Parameter(Position=0,Mandatory=$false)]
  [ValidateSet('dev:setup','dev:up','dev:all','worker:start','audit:full','smoke:test','login:test','history:smoke','discipline:bootstrap-rbac','discipline:smoke')]
  [string]$Task,

  [switch]$List,
  [switch]$WhatIf,
  [switch]$Confirm,
  [switch]$Help,

  # Passthrough for login:test
  [Parameter(Mandatory=$false)] [string]$BaseUrl,
  [Parameter(Mandatory=$false)] [string]$Username,
  [Parameter(Mandatory=$false)] [string]$Password,
  [Parameter(Mandatory=$false)] [string]$Token,
  [switch]$SkipCertificateCheck,

  # Passthrough for smoke scripts
  [Parameter(Mandatory=$false)] [int]$HttpPort
)

# Capture any unbound arguments to forward (e.g., to login_test.ps1)
$script:UNBOUND = $args

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# Resolve repo root
$Root = Resolve-Path (Join-Path $PSScriptRoot '..')
Set-Location $Root

function Write-Header($t){ Write-Host ("== {0} ==" -f $t) -ForegroundColor Cyan }

function Get-HttpsPort {
  $portFile = Join-Path $Root 'backend\.runtime\https_port.txt'
  $port = 8443
  if (Test-Path -Path $portFile) {
    try { $raw = Get-Content -Path $portFile -ErrorAction Stop | Select-Object -First 1; if ($raw) { $port = [int]$raw } } catch { }
  }
  return $port
}

function Show-Help {
  Write-Header 'exec_hub help'
  $port = Get-HttpsPort
  Write-Host 'Usage:'
  Write-Host '  pwsh -File scripts/exec_hub.ps1 -List' -ForegroundColor DarkGray
  Write-Host '  pwsh -File scripts/exec_hub.ps1 <task> [-WhatIf] [-Confirm]' -ForegroundColor DarkGray
  Write-Host ''
  Write-Host 'Tasks:'
  Show-List
  Write-Host ''
  Write-Host ("Detected HTTPS port: {0}" -f $port) -ForegroundColor DarkCyan
  Write-Host ("Quick smoke: pwsh -File scripts/exec_hub.ps1 smoke:test") -ForegroundColor DarkCyan
}

function Ensure-Venv {
  $act = Join-Path $Root '.venv\Scripts\Activate.ps1'
  if (Test-Path $act) { try { . $act } catch {} }
}

function Simulate($cmd){
  if ($WhatIf) { Write-Host ("[WhatIf] {0}" -f $cmd) -ForegroundColor DarkYellow; return $true }
  return $false
}

function Require-Confirm($label){
  if ($Confirm) { return $true }
  $r = Read-Host ("[Confirm] Execute '{0}'? (y/N)" -f $label)
  return ($r -match '^(y|yes)$')
}

function Task-DevSetup {
  $script = 'scripts/dev_setup.ps1'
  Write-Header 'dev:setup'
  if (Simulate $script) { return }
  & pwsh -File $script
}

function Task-DevUp {
  $script = 'scripts/dev_up.ps1'
  Write-Header 'dev:up'
  if (Simulate $script) { return }
  & pwsh -File $script
}

function Task-DevAll {
  $script = 'scripts/dev_all.ps1'
  Write-Header 'dev:all'
  if (Simulate $script) { return }
  & pwsh -File $script
}

function Task-WorkerStart {
  $script = 'scripts/rq_worker.ps1'
  Write-Header 'worker:start'
  $args = @('-Queue','default')
  $cmd = "pwsh -File $script $($args -join ' ')"
  if (Simulate $cmd) { return }
  & pwsh -File $script @args
}

function Task-AuditFull {
  $script = 'scripts/full_audit.ps1'
  Write-Header 'audit:full'
  if (Simulate $script) { return }
  & pwsh -File $script
}

function Task-SmokeTest {
  $script = 'scripts/dev_smoke.ps1'
  Write-Header 'smoke:test'
  if (-not (Test-Path $script)) { Write-Error "Missing $script"; return }
  $forward = @('-HttpsOnly')
  if ($PSBoundParameters.ContainsKey('HttpPort') -and $HttpPort) { $forward += @('-HttpPort', $HttpPort) }
  $cmd = "pwsh -File $script $($forward -join ' ')"
  if (Simulate $cmd) { return }
  & pwsh -File $script @forward
}

function Task-HistorySmoke {
  $script = 'scripts/history_smoke.ps1'
  Write-Header 'history:smoke'
  if (-not (Test-Path $script)) { Write-Error "Missing $script"; return }
  $forward = @('-HttpsOnly')
  if ($PSBoundParameters.ContainsKey('HttpPort') -and $HttpPort) { $forward += @('-HttpPort', $HttpPort) }
  $cmd = "pwsh -File $script $($forward -join ' ')"
  if (Simulate $cmd) { return }
  & pwsh -File $script @forward
}

function Task-LoginTest {
  $script = 'scripts/login_test.ps1'
  Write-Header 'login:test'
  if (-not (Test-Path $script)) { Write-Error "Missing $script"; return }
  $forward = @()
  if ($BaseUrl) { $forward += @('-BaseUrl', $BaseUrl) }
  if ($Username) { $forward += @('-Username', $Username) }
  if ($Password) { $forward += @('-Password', $Password) }
  if ($SkipCertificateCheck) { $forward += @('-SkipCertificateCheck') }
  # Also include any truly unbound args if provided
  if ($script:UNBOUND -and $script:UNBOUND.Length -gt 0) { $forward += $script:UNBOUND }
  $cmd = "pwsh -File $script $($forward -join ' ')"
  if (Simulate $cmd) { return }
  & pwsh -File $script @forward
}

function Task-DisciplineBootstrapRbac {
  Write-Header 'discipline:bootstrap-rbac'
  $manage = Join-Path $Root 'backend\manage.py'
  if (-not (Test-Path $manage)) { Write-Error "Missing backend/manage.py"; return }
  $args = @('manage.py','bootstrap_discipline_rbac','--with-access')
  $cmd = "python " + ($args -join ' ')
  if ($WhatIf) { Write-Host ("[WhatIf] {0}" -f $cmd) -ForegroundColor DarkYellow; return }
  if (-not (Require-Confirm $cmd)) { Write-Host 'Aborted.' -ForegroundColor DarkGray; return }
  Push-Location (Join-Path $Root 'backend')
  try {
    & python @('manage.py','bootstrap_discipline_rbac','--with-access')
  } finally {
    Pop-Location
  }
}

function Show-List {
  Write-Header 'Available tasks'
  $rows = @(
    @{Key='dev:setup';Desc='Create/repair venv + dev tools (black/flake8) + generator check'}
    @{Key='dev:up';Desc='Bring up Postgres/Redis + migrate + ensure superuser + HTTPS + RQ worker'}
    @{Key='dev:all';Desc='Start backend (HTTPS) and then frontend (Vite)'}
    @{Key='worker:start';Desc='Start RQ worker on queue "default"'}
    @{Key='audit:full';Desc='Django checks + migrations status + healthcheck'}
    @{Key='smoke:test';Desc='Quick HTTPS smoke: /livez, /healthz, and 401 for protected API'}
    @{Key='history:smoke';Desc='Quick HTTPS smoke for attendance history: expect 401 without token'}
    @{Key='login:test';Desc='Obtain JWT, call /api/me, trigger refresh; prints a concise auth report'}
    @{Key='discipline:bootstrap-rbac';Desc='Create/refresh discipline role groups and permissions (idempotent)'}
    @{Key='discipline:smoke';Desc='Diagnose discipline incidents visibility: counts, samples, list (requires auth token)'}
  )
  $rows | ForEach-Object { Write-Host ("- {0} : {1}" -f $_.Key, $_.Desc) }
  Write-Host "Use: pwsh -File scripts/exec_hub.ps1 <task> [-WhatIf] [-Confirm]" -ForegroundColor DarkGray
}

# Optional preflight recommendations
try { & pwsh -File 'scripts/preflight.ps1' } catch { Write-Host 'Preflight skipped.' -ForegroundColor DarkGray }

Ensure-Venv

if ($Help) { Show-Help; exit 0 }

if ($List -or -not $Task) { Show-List; exit 0 }

switch ($Task) {
  'dev:setup'     { Task-DevSetup }
  'dev:up'        { Task-DevUp }
  'dev:all'       { Task-DevAll }
  'worker:start'  { Task-WorkerStart }
  'audit:full'    { Task-AuditFull }
  'smoke:test'    { Task-SmokeTest }
  'history:smoke' { Task-HistorySmoke }
  'login:test'    { Task-LoginTest }
  'discipline:bootstrap-rbac' { Task-DisciplineBootstrapRbac }
  'discipline:smoke' { 
    Write-Header 'discipline:smoke'
    $script = 'scripts/discipline_smoke.ps1'
    if (-not (Test-Path $script)) { Write-Error "Missing $script"; exit 1 }
    $forward = @()
    if ($PSBoundParameters.ContainsKey('BaseUrl') -and $BaseUrl) { $forward += @('-BaseUrl', $BaseUrl) }
    if ($PSBoundParameters.ContainsKey('Token') -and $Token) { $forward += @('-Token', $Token) }
    if ($PSBoundParameters.ContainsKey('SkipCertificateCheck') -and $SkipCertificateCheck) { $forward += @('-SkipCertificateCheck') }
    $cmd = "pwsh -File $script $($forward -join ' ')"
    if (Simulate $cmd) { return }
    & pwsh -File $script @forward
  }
  default         { Write-Error "Unknown task: $Task"; exit 1 }
}