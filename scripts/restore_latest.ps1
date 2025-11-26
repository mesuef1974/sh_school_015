#requires -Version 5.1
param(
  [string]$BackupDir,
  [switch]$StrictVerify,
  [switch]$SkipDrop,
  [switch]$Force,
  [Alias('y')][switch]$AssumeYes
)

<#
الغرض: استعادة أحدث نسخة احتياطية بسهولة.

الاستخدام:
  PowerShell: ./scripts/restore_latest.ps1
  PowerShell: ./scripts/restore_latest.ps1 -BackupDir "D:\sh_school_015\backups"
  PowerShell: ./scripts/restore_latest.ps1 -StrictVerify

ملاحظات:
- يقوم هذا السكربت داخليًا بمناداة scripts/db_restore.ps1 مع الخيار -Latest.
- يتم تمرير -Force افتراضيًا لتخطي التأكيد التفاعلي.
- يمكنك استخدام -SkipDrop للحفاظ على المحتوى الحالي دون إسقاط المخطط public أولًا.
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# جذر المشروع
$Root = Resolve-Path (Join-Path $PSScriptRoot '..')
Set-Location $Root

$restoreScript = Join-Path $Root 'scripts\db_restore.ps1'
if (-not (Test-Path -LiteralPath $restoreScript)) {
  Write-Error "لم يتم العثور على السكربت المطلوب: $restoreScript"
  exit 1
}

# بناء معاملات التحويل إلى db_restore.ps1 باستخدام splatting مُسمّى لتجنّب الخلط بين المعاملات الموضعية
$splat = @{
  Latest = $true
  Force  = $true  # تمرير Force افتراضيًا لتخطي التأكيد
}
if ($BackupDir -and $BackupDir.Trim() -ne '') { $splat['BackupDir'] = $BackupDir }
if ($StrictVerify) { $splat['StrictVerify'] = $true }
if ($SkipDrop)     { $splat['SkipDrop']     = $true }

Write-Host 'سيتم استعادة أحدث نسخة احتياطية من المجلد المحدد (أو مجلد backups الافتراضي).' -ForegroundColor Cyan
& $restoreScript @splat
