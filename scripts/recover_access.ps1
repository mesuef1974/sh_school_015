#requires -Version 5.1
param(
  [Parameter(Mandatory = $true)] [string]$Username,
  [string]$Email = "",
  [Parameter(Mandatory = $true)] [string]$Password,
  [switch]$MakeSuper = $true
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# Move to repo root
$Root = Resolve-Path (Join-Path $PSScriptRoot '..')
Set-Location $Root

# Activate venv if exists
$VenvActivate = Join-Path $Root '.venv\Scripts\Activate.ps1'
if (Test-Path $VenvActivate) { try { . $VenvActivate } catch { } }

# Build args for ensure_superuser (supports CLI args in school app)
$argsList = @('--username', $Username, '--password', $Password)
if ($Email -and $Email.Trim() -ne '') { $argsList += @('--email', $Email) }

Write-Host "Ensuring superuser '$Username' ..." -ForegroundColor Cyan
python backend\manage.py ensure_superuser @argsList

# Force activate + super flags just in case (idempotent)
$pyUsername = "'$Username'"
$pyMakeSuper = if ($MakeSuper) { 'True' } else { 'False' }

$py = @"
from django.contrib.auth import get_user_model
User = get_user_model()
username = $pyUsername
make_super = $pyMakeSuper

u = User.objects.filter(username=username).first()
if not u:
    print(f'User not found: {username}')
else:
    changed = False
    if not u.is_active:
        u.is_active = True
        changed = True
    if make_super:
        if not u.is_staff:
            u.is_staff = True
            changed = True
        if not u.is_superuser:
            u.is_superuser = True
            changed = True
    if changed:
        u.save(update_fields=['is_active','is_staff','is_superuser'])
        print(f'User flags updated for {u.username}')
    else:
        print(f'User flags OK for {u.username}')
"@

# Execute the Python snippet using Django shell (PowerShell does not support Bash-style heredocs like <<)
$runtimeDir = Join-Path $Root 'backend\.runtime'
if (-not (Test-Path $runtimeDir)) { New-Item -ItemType Directory -Path $runtimeDir | Out-Null }
$tmpPy = Join-Path $runtimeDir 'recover_access_inline.py'
Set-Content -LiteralPath $tmpPy -Value $py -Encoding UTF8

# Execute the Python snippet via Django shell using -c (works in PowerShell 5/7 without '<' redirection)
$pyExec = "import runpy; runpy.run_path(r'$tmpPy', run_name='__main__')"
python backend\manage.py shell -c $pyExec

# Best-effort cleanup of the temporary file
try { Remove-Item -LiteralPath $tmpPy -Force -ErrorAction SilentlyContinue } catch { }

Write-Host ''
Write-Host 'Next steps:' -ForegroundColor Green
Write-Host '1) افتح صفحة تسجيل الدخول الخلفية:'
Write-Host '   https://127.0.0.1:8443/accounts/login/' -ForegroundColor Yellow
Write-Host ('2) سجّل الدخول باسم المستخدم: {0} وكلمة المرور التي أدخلتها.' -f $Username)
Write-Host '3) للواجهة الأمامية، شغّل:'
Write-Host '   ./scripts/dev_all.ps1 -ForceFrontend' -ForegroundColor Yellow
Write-Host '   ثم افتح عنوان Vite الظاهر في الطرفية. تأكد أن المتصفح يقبل الشهادة المحلية.'
