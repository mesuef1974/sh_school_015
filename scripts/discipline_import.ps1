#requires -Version 5.1
<#!
.SYNOPSIS
  احترافي: أمر واحد لاستيراد كتالوج المخالفات من ملف JSON وتجهيز قاعدة البيانات تلقائياً.

.DESCRIPTION
  يقوم هذا السكربت بما يلي:
    - تفعيل البيئة الافتراضية إن وجدت (.venv)
    - اختيار ملف JSON تلقائياً من DOC\school_DATA\violations_detailed.json إذا لم يُحدَّد
    - التحقق من وجود الملف
    - تشغيل Django مع أمر ensure_discipline_data (يشمل فحص الاتصال بقاعدة البيانات + تطبيق الترحيلات + التحميل)
      أو يمكن التحويل إلى التحميل المباشر load_discipline_catalog عبر -SkipEnsure

.PARAMETER File
  مسار ملف JSON المطلوب استيراده. افتراضياً يستخدم مسار المستودع: DOC\school_DATA\violations_detailed.json

.PARAMETER Purge
  حذف السجلات السابقة قبل الاستيراد (تفريغ BehaviorLevel و Violation)

.PARAMETER SkipEnsure
  إن أردت تخطي ensure_discipline_data وتشغيل load_discipline_catalog مباشرةً.

.PARAMETER AutoDb
  محاولة تشغيل/إصلاح قاعدة البيانات محلياً تلقائياً (scripts\db_up.ps1) ثم إعادة المحاولة مرة واحدة عند فشل الاتصال.

.EXAMPLE
  pwsh -File scripts\discipline_import.ps1

.EXAMPLE
  pwsh -File scripts\discipline_import.ps1 -Purge

.EXAMPLE
  pwsh -File scripts\discipline_import.ps1 -File "D:\sh_school_015\DOC\school_DATA\violations_detailed.json" -Purge

.NOTES
  بعد الاستيراد، افتح:
    https://127.0.0.1:8443/admin/discipline/
!#>
Param(
  [string]$File = '',
  [switch]$Purge = $false,
  [switch]$SkipEnsure = $false,
  [switch]$AutoDb = $false
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# الانتقال إلى جذر المستودع
$Root = Resolve-Path (Join-Path $PSScriptRoot '..')
Set-Location $Root

# تفعيل البيئة الافتراضية إذا وجدت
$VenvActivate = Join-Path $Root '.venv\Scripts\Activate.ps1'
if (Test-Path -LiteralPath $VenvActivate) { try { . $VenvActivate } catch { } }

# اختيار الملف الافتراضي إذا لم يُمرر
$DefaultJson = Join-Path $Root 'DOC\school_DATA\violations_detailed.json'
if (-not $File -or $File.Trim() -eq '') { $File = $DefaultJson }

if (-not (Test-Path -LiteralPath $File)) {
  throw "JSON file not found: $File"
}

Push-Location (Join-Path $Root 'backend')
try {
  $argsList = @('manage.py')
  if (-not $SkipEnsure) {
    $argsList += @('ensure_discipline_data')
  } else {
    $argsList += @('load_discipline_catalog')
  }
  if ($Purge) { $argsList += '--purge' }
  if ($File) { $argsList += @('--file', $File) }

  Write-Host "Using JSON: $File" -ForegroundColor Cyan
  if ($env:PYTHON) {
    & $env:PYTHON @argsList
  } else {
    python @argsList
  }
  $exit = $LASTEXITCODE

  # Auto DB self-heal and single retry when requested
  if ($exit -ne 0 -and $AutoDb) {
    Write-Host ''
    Write-Host '[AutoDb] محاولة تشغيل/إصلاح قاعدة البيانات عبر scripts\db_up.ps1 ثم إعادة المحاولة ...' -ForegroundColor DarkYellow
    try {
      & pwsh -File (Join-Path $Root 'scripts\db_up.ps1')
    } catch {
      Write-Host ('[AutoDb] فشل تشغيل db_up.ps1: {0}' -f $_.Exception.Message) -ForegroundColor Red
    }

    # If db_up picked a free host port (when 5432 is busy), honor it for the retry.
    try {
      $runtimePortFile = Join-Path $Root 'backend\.runtime\pg_port.txt'
      if (Test-Path -LiteralPath $runtimePortFile) {
        $retryPort = Get-Content -LiteralPath $runtimePortFile -ErrorAction Stop | Select-Object -First 1
        if ($retryPort -and $retryPort.Trim() -match '^[0-9]+$') {
          $retryPort = $retryPort.Trim()
          $env:PG_HOST = '127.0.0.1'
          $env:PG_PORT = $retryPort
          Write-Host ("[AutoDb] استخدام المنفذ المكتشف لإعادة المحاولة: PG_HOST=127.0.0.1, PG_PORT={0}" -f $retryPort) -ForegroundColor DarkCyan

          # Additionally, set DATABASE_URL for frameworks/settings that prefer it over PG_* vars
          # Read backend/.env to pick user/password/db with safe fallbacks
          $pgUser = 'postgres'; $pgPass = 'postgres'; $pgDb = 'sh_school'
          try {
            $envFile = Join-Path $Root 'backend\.env'
            if (Test-Path -LiteralPath $envFile) {
              Get-Content -LiteralPath $envFile | Where-Object { $_ -and ($_ -notmatch '^\s*#') } | ForEach-Object {
                if ($_ -match '^(?<k>[^=\s]+)=(?<v>.*)$') {
                  $k = $Matches['k'].Trim(); $v = $Matches['v'].Trim()
                  # strip surrounding quotes if any
                  if ($v.Length -ge 2) {
                    $first = $v[0]; $last = $v[$v.Length-1]
                    if (($first -eq '"' -and $last -eq '"') -or ($first -eq "'" -and $last -eq "'")) { $v = $v.Substring(1, $v.Length - 2) }
                  }
                  switch -Regex ($k) {
                    '^PG_USER$'      { if ($v) { $pgUser = $v } }
                    '^DB_USER$'      { if ($v -and $pgUser -eq 'postgres') { $pgUser = $v } }
                    '^PG_PASSWORD$'  { if ($v) { $pgPass = $v } }
                    '^DB_PASSWORD$'  { if ($v -and $pgPass -eq 'postgres') { $pgPass = $v } }
                    '^PG_DB$'        { if ($v) { $pgDb = $v } }
                    '^DB_NAME$'      { if ($v -and $pgDb -eq 'sh_school') { $pgDb = $v } }
                  }
                }
              }
            }
          } catch { }

          try {
            $passEncoded = [System.Uri]::EscapeDataString([string]$pgPass)
            $dsn = "postgres://$($pgUser):$($passEncoded)@127.0.0.1:$retryPort/$pgDb"
            $env:DATABASE_URL = $dsn
            $masked = "postgres://$($pgUser):****@127.0.0.1:$retryPort/$pgDb"
            Write-Host ("[AutoDb] DATABASE_URL تم ضبطه للمحاولة الثانية: {0}" -f $masked) -ForegroundColor DarkCyan
          } catch {
            Write-Host ('[AutoDb] فشل إعداد DATABASE_URL: {0}' -f $_.Exception.Message) -ForegroundColor DarkYellow
          }
        }
      }
    } catch {
      Write-Host ('[AutoDb] تعذر قراءة backend\.runtime\pg_port.txt: {0}' -f $_.Exception.Message) -ForegroundColor DarkYellow
    }

    Write-Host '[AutoDb] إعادة المحاولة الآن ...' -ForegroundColor DarkYellow
    if ($env:PYTHON) {
      & $env:PYTHON @argsList
    } else {
      python @argsList
    }
    $exit = $LASTEXITCODE
  }

  if ($exit -ne 0) {
    Write-Host ''
    Write-Host "حدث خطأ أثناء الاستيراد (رمز الخروج: $exit)." -ForegroundColor Red
    Write-Host "تحقق من إعدادات قاعدة البيانات (backend\.env: PG_DB, PG_USER, PG_PASSWORD, PG_HOST, PG_PORT) أو وفّر DATABASE_URL." -ForegroundColor Yellow
    Write-Host ''
    Write-Host "استخدم أحد الأوامر التالية (انسخ السطر فقط دون النصوص أعلاه):" -ForegroundColor Yellow
    # Retry with automatic DB startup/repair then import
    Write-Host ("pwsh -File scripts\discipline_import.ps1 -AutoDb -File `"{0}`"" -f $File) -ForegroundColor Yellow
    # Force reinitialize local DB (destructive for local data)
    Write-Host "pwsh -File scripts\db_up.ps1 -ForceReinit" -ForegroundColor Yellow
    # Direct load without ensure step
    Write-Host ("pwsh -File scripts\discipline_import.ps1 -SkipEnsure -File `"{0}`"" -f $File) -ForegroundColor Yellow
    exit $exit
  }

  Write-Host 'تم الاستيراد بنجاح. افتح العنوان التالي للمراجعة:' -ForegroundColor Green
  Write-Host '  https://127.0.0.1:8443/admin/discipline/' -ForegroundColor Green
}
finally {
  Pop-Location
}
