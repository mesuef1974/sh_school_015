param(
    [ValidateSet('dev-all','verify','up-services','stop-services','start-backend','help')]
    [string]$Task,
    [switch]$SkipPostgresTests,
    [switch]$StartBackend
)

$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSCommandPath
$RepoRoot = Resolve-Path (Join-Path $Root '..')
$Ops = Join-Path $RepoRoot 'scripts\ops_run.ps1'
if (-not (Test-Path $Ops)) {
    Write-Error "Cannot find scripts/ops_run.ps1 at $Ops"
}

function Run-Ops {
    param(
        [string]$Name
    )
    $argsList = @('-File', $Ops, '-Task', $Name)
    if ($SkipPostgresTests -and $Name -eq 'verify') { $argsList += '-SkipPostgresTests' }
    if ($StartBackend -and $Name -eq 'verify') { $argsList += '-StartBackend' }
    pwsh @argsList
}

if ($Task) {
    Run-Ops -Name $Task
    exit $LASTEXITCODE
}

# Interactive menu
Write-Host "=============================" -ForegroundColor Cyan
Write-Host "  SH School – Quick Launcher  " -ForegroundColor Cyan
Write-Host "=============================" -ForegroundColor Cyan
Write-Host "اختَر مهمة للتشغيل:" -ForegroundColor Yellow
Write-Host "  1) تشغيل الكل (dev-all)"
Write-Host "  2) تحقق شبيه CI (verify)"
Write-Host "  3) تشغيل خدمات Docker (up-services)"
Write-Host "  4) إيقاف خدمات Docker (stop-services)"
Write-Host "  5) تشغيل الباكيند فقط (start-backend)"
Write-Host "  6) المساعدة (help)"
Write-Host "  0) خروج"

$choice = Read-Host "أدخل الرقم المطلوب"

switch ($choice) {
    '1' { Run-Ops 'dev-all' }
    '2' {
        $extra = Read-Host 'تخطي اختبارات PostgreSQL؟ (y/N)'
        if ($extra -match '^(y|Y)') { $global:SkipPostgresTests = $true }
        $start = Read-Host 'تشغيل الباكيند مؤقتًا قبل الفحوص؟ (y/N)'
        if ($start -match '^(y|Y)') { $global:StartBackend = $true }
        Run-Ops 'verify'
    }
    '3' { Run-Ops 'up-services' }
    '4' { Run-Ops 'stop-services' }
    '5' { Run-Ops 'start-backend' }
    '6' { Run-Ops 'help' }
    '0' { Write-Host 'وداعًا!'; exit 0 }
    default { Write-Host 'خيار غير معروف'; exit 1 }
}

exit $LASTEXITCODE
