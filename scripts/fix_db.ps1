#requires -Version 5.1
<#!
Quick fixer for an "empty" local development database.

What it does:
  1) Starts/aligns the local PostgreSQL container via scripts/db_up.ps1
  2) If a backup exists in backups\, imports the latest backup (drop+restore) via scripts/import_backup.ps1
  3) Otherwise, applies Django migrations, ensures a superuser, and prints quick health stats

Usage:
  pwsh -File scripts/fix_db.ps1

Notes:
- Reads PG_* from backend/.env; db_up.ps1 already handles common auth/volume mismatches.
- This is non-destructive only if no backup is found. If a backup exists, it will DROP schema public then restore (unless you change the flag below).
!#>
Param(
  [switch]$SkipDrop,     # forward to import script if you want to keep current schema
  [switch]$AssumeYes     # auto-confirm prompts
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# Move to repo root
$Root = Resolve-Path (Join-Path $PSScriptRoot '..')
Set-Location $Root

Write-Host '== Sh-School | Fix Local Database ==' -ForegroundColor Cyan

# Activate venv if present
$venv = Join-Path $Root '.venv\Scripts\Activate.ps1'
if (Test-Path -LiteralPath $venv) { try { . $venv } catch { } }

# Ensure Python available
try { python --version *> $null } catch { Write-Error 'Python not found on PATH. Activate .venv first: .\.venv\Scripts\Activate.ps1'; exit 1 }

# 1) Ensure Postgres is up
Write-Host '[fix_db] Ensuring PostgreSQL is up ...' -ForegroundColor DarkGray
& (Join-Path $Root 'scripts\db_up.ps1')

# Helper: run a tiny Django probe and counts
function Invoke-DbProbe {
  try {
    $code = @"
import os, sys
p = r'backend'
if p not in sys.path: sys.path.insert(0, p)
os.environ.setdefault('DJANGO_SETTINGS_MODULE','core.settings')
try:
    import django
    django.setup()
    from django.db import connection
    from django.contrib.auth import get_user_model
    User = get_user_model()
    with connection.cursor() as c:
        c.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public'")
        tbls = c.fetchone()[0]
    counts = {
        'auth_user': User.objects.count(),
    }
    # Optional key domain tables
    try:
        from school.models import Student, Class, TeachingAssignment
        counts['school_student'] = Student.objects.count()
        counts['school_class'] = Class.objects.count()
        counts['school_teachingassignment'] = TeachingAssignment.objects.count()
    except Exception:
        pass
    print('DB_OK tables=', tbls, ' stats=', counts)
    raise SystemExit(0)
except Exception as e:
    print(type(e).__name__, e)
    raise SystemExit(1)
"@
    $tmp = New-TemporaryFile
    Set-Content -Path $tmp -Value $code -Encoding UTF8
    $out = & python $tmp 2>&1
    $codeExit = $LASTEXITCODE
    Remove-Item $tmp -ErrorAction SilentlyContinue
    return @{ exit=$codeExit; output=($out | Out-String) }
  } catch { return @{ exit=1; output=$_.Exception.Message } }
}

# 2) If backups exist, import the latest
$backupsDir = Join-Path $Root 'backups'
$hasBackup = $false
if (Test-Path -LiteralPath $backupsDir) {
  $supported = @('*.dump','*.backup','*.tar','*.sql','*.sql.gz')
  $files = Get-ChildItem -LiteralPath $backupsDir -File -Include $supported -ErrorAction SilentlyContinue
  if ($files -and $files.Count -gt 0) { $hasBackup = $true }
}

if ($hasBackup) {
  Write-Host '[fix_db] Found backups. Importing the latest (this will drop schema public) ...' -ForegroundColor Yellow
  $importScript = Join-Path $Root 'scripts\import_backup.ps1'
  $importParams = @{}
  $importParams['Latest'] = $true
  if ($AssumeYes) { $importParams['AssumeYes'] = $true }
  if ($SkipDrop)  { $importParams['SkipDrop']  = $true }
  $importOutput = & $importScript @importParams 2>&1
  $importExit = $LASTEXITCODE
  if ($importExit -ne 0) {
    $txt = ($importOutput | Out-String)
    # If failure is due to connectivity/auth probe, try auto reinitialization once
    if ($txt -match 'Database connectivity probe failed' -or $txt -match 'password authentication failed') {
      Write-Warning "[fix_db] Import failed due to DB connectivity/auth. Attempting automatic reinitialization of Postgres volume, then retrying import once ..."
      & (Join-Path $Root 'scripts\db_up.ps1') -ForceReinit
      # Retry import once
      $importOutput2 = & $importScript @importParams 2>&1
      $importExit2 = $LASTEXITCODE
      if ($importExit2 -ne 0) {
        Write-Error "Import failed after auto-reinit (exit $importExit2). Details:\n$($importOutput2 | Out-String)"
        exit $importExit2
      }
    } else {
      Write-Error "Import failed with exit code $importExit. Details:\n$txt"
      exit $importExit
    }
  }
} else {
  Write-Host '[fix_db] No backups found. Applying migrations and ensuring superuser ...' -ForegroundColor DarkYellow
  Push-Location (Join-Path $Root 'backend')
  try {
    python manage.py migrate --noinput
    if ($LASTEXITCODE -ne 0) { throw "migrate exited with code $LASTEXITCODE" }
    # Ensure a sensible local superuser (from .env if present)
    $envFile = Join-Path $Root 'backend\.env'
    $su = 'mesuef'
    if (Test-Path -LiteralPath $envFile) {
      $envVars = @{}
      Get-Content $envFile | Where-Object { $_ -and ($_ -notmatch '^\s*#') } | ForEach-Object {
        if ($_ -match '^(?<k>[^=\s]+)=(?<v>.*)$') { $envVars[$Matches['k'].Trim()] = $Matches['v'].Trim() }
      }
      if ($envVars['DJANGO_SUPERUSER_USERNAME']) { $su = $envVars['DJANGO_SUPERUSER_USERNAME'] }
      if ($envVars['DJANGO_SUPERUSER_EMAIL']) { $env:DJANGO_SUPERUSER_EMAIL = $envVars['DJANGO_SUPERUSER_EMAIL'] }
      if ($envVars['DJANGO_SUPERUSER_PASSWORD']) { $env:DJANGO_SUPERUSER_PASSWORD = $envVars['DJANGO_SUPERUSER_PASSWORD'] }
      $env:DJANGO_SUPERUSER_USERNAME = $su
    }
    python manage.py ensure_superuser --username $su | Out-Null
  } finally { Pop-Location }
}

# 3) Probe and summarize
$probe = Invoke-DbProbe
if ($probe.exit -eq 0) {
  Write-Host "[fix_db] Probe OK: $($probe.output.Trim())" -ForegroundColor Green
  Write-Host 'Done. You can now run: pwsh -File scripts/dev_up.ps1' -ForegroundColor DarkGray
  exit 0
} else {
  Write-Warning "[fix_db] Probe reported issues:\n$($probe.output)"
  Write-Host 'Try reinitializing the DB volume and re-running:' -ForegroundColor DarkYellow
  Write-Host '  pwsh -File scripts/db_up.ps1 -ForceReinit' -ForegroundColor DarkYellow
  Write-Host '  pwsh -File scripts/fix_db.ps1 -AssumeYes' -ForegroundColor DarkYellow
  exit 1
}
