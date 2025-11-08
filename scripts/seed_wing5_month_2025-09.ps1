#requires -Version 5.1
<#!
Purpose:
  End-to-end script to seed a full month (4 Sun→Thu weeks) of realistic, approved, locked demo data
  for Wing 5 starting from 2025-09-14, including ExitEvent and AbsenceAlert, with safe cleanup before seeding
  and basic post-run verification. Designed to be idempotent and re-runnable.

Usage:
  - Open PowerShell at the repository root and run:
      scripts\seed_wing5_month_2025-09.ps1
  - The script will:
      * Activate venv if available
      * Preview cleanup (dry-run)
      * Clean the target range (with --yes)
      * Seed the month (teacher + supervisor phases, approved & locked)
      * Verify weekends (Fri/Sat) are empty within the range
      * Write a detailed log under backend\.runtime\logs

Notes:
  - Requires Django manage.py to be functional in the current environment.
  - Uses conservative parameters: P1-2 absent ≈ 10%, deterministic seed=24680.
  - All generated data is realistic-demo and safe to re-run (idempotent within the range).
!#>

Param(
  [int]$WingId = 5,
  [datetime]$Start = [datetime]::Parse('2025-09-14'),
  [int]$Weeks = 4,
  [double]$P12Absent = 0.10,
  [int]$Seed = 24680
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# Resolve repo root and switch to it
$Root = Resolve-Path (Join-Path $PSScriptRoot '..')
Set-Location $Root

# Ensure backend runtime log folder exists
$RuntimeDir = Join-Path $Root 'backend\.runtime\logs'
if (-not (Test-Path $RuntimeDir)) { New-Item -ItemType Directory -Path $RuntimeDir | Out-Null }
$ts = (Get-Date).ToString('yyyyMMdd_HHmmss')
$LogFile = Join-Path $RuntimeDir ("seed_wing{0}_month_{1}_w{2}_{3}.log" -f $WingId, $Start.ToString('yyyyMMdd'), $Weeks, $ts)

# Helper to run manage.py with timestamped logging
function Invoke-Manage {
  param(
    [Parameter(Mandatory=$true)][string]$Args,
    [switch]$Quiet
  )
  $prefix = (Get-Date).ToString('[yyyy-MM-dd HH:mm:ss] ')
  $cmd = "python manage.py $Args"
  if (-not $Quiet) { Write-Host ("`n$prefix$cmd") -ForegroundColor Cyan }
  Add-Content -LiteralPath $LogFile -Value ("`n$prefix$cmd")
  # Execute and capture output using .NET Process to avoid same-file redirect bug
  $psi = New-Object System.Diagnostics.ProcessStartInfo
  $psi.FileName = 'python'
  $psi.Arguments = "manage.py $Args"
  $psi.RedirectStandardOutput = $true
  $psi.RedirectStandardError = $true
  $psi.UseShellExecute = $false
  $psi.CreateNoWindow = $true
  $proc = New-Object System.Diagnostics.Process
  $proc.StartInfo = $psi
  $null = $proc.Start()
  $stdOut = $proc.StandardOutput.ReadToEnd()
  $stdErr = $proc.StandardError.ReadToEnd()
  $proc.WaitForExit()
  if ($stdOut) { Add-Content -LiteralPath $LogFile -Value $stdOut }
  if ($stdErr) { Add-Content -LiteralPath $LogFile -Value $stdErr }
  if ($proc.ExitCode -ne 0) {
    Write-Warning ("Command failed (exit $($proc.ExitCode)) → $cmd. Check log: $LogFile")
    throw "manage.py command failed: $Args"
  }
}

# Activate venv if available
$VenvActivate = Join-Path $Root '.venv\Scripts\Activate.ps1'
if (Test-Path -Path $VenvActivate) { try { . $VenvActivate } catch { } }

# Compute end date based on 4 Sun→Thu weeks (the monthly command will handle this as well)
$End = $Start.AddDays(27) # inclusive upper bound covering 4 school weeks in calendar (~28 days)

Write-Host "Seeding Wing $WingId from $($Start.ToString('yyyy-MM-dd')) for $Weeks weeks (approx end: $($End.ToString('yyyy-MM-dd')))" -ForegroundColor Green
Write-Host "Log: $LogFile" -ForegroundColor DarkGray

# 1) Dry-run cleanup preview for the exact range
Invoke-Manage -Args ("cleanup_attendance_range --start {0} --end {1} --wing {2} --dry-run" -f $Start.ToString('yyyy-MM-dd'), $End.ToString('yyyy-MM-dd'), $WingId)

# 2) Perform cleanup (AR/AD/EE) for the range
Invoke-Manage -Args ("cleanup_attendance_range --start {0} --end {1} --wing {2} --yes" -f $Start.ToString('yyyy-MM-dd'), $End.ToString('yyyy-MM-dd'), $WingId)

# 3) Seed a month (4 Sun→Thu weeks), approved & finalized with exits and alerts
Invoke-Manage -Args ("seed_wing_month_demo --wing {0} --start {1} --weeks {2} --workflow all --approve --finalize --with-exits --with-alerts --p12-absent {3} --seed {4} --summary" -f $WingId, $Start.ToString('yyyy-MM-dd'), $Weeks, ([string]::Format([System.Globalization.CultureInfo]::InvariantCulture, '{0:F2}', $P12Absent)), $Seed)

# 4) Verify weekends (Fri/Sat) are empty within the range
Invoke-Manage -Args ("cleanup_attendance_weekends --start {0} --end {1} --wing {2} --dry-run" -f $Start.ToString('yyyy-MM-dd'), $End.ToString('yyyy-MM-dd'), $WingId)

Write-Host "Done. Review the log file for summaries and counts:" -ForegroundColor Green
Write-Host "  $LogFile" -ForegroundColor DarkGray
