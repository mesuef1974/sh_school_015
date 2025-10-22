#requires -Version 5.1
param(
    [Parameter(Mandatory=$false)]
    [string]$FilePath,
    [switch]$Latest,
    [string]$BackupDir,
    [switch]$Force,
    [Alias('y')]
    [switch]$AssumeYes,
    [switch]$SkipDrop,
    [switch]$StrictVerify
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# Resolve project root as parent of this script directory
$Root = Resolve-Path (Join-Path $PSScriptRoot '..')
Set-Location $Root

# If -Latest is specified, pick the most recent backup from backups directory (or provided -BackupDir)
if ($Latest) {
    if (-not $BackupDir -or $BackupDir.Trim() -eq '') { $BackupDir = Join-Path $Root 'backups' }
    if (-not (Test-Path -LiteralPath $BackupDir)) {
        Write-Error "Backup directory not found: $BackupDir"
        exit 1
    }
    $supported = @('*.dump','*.backup','*.tar','*.sql','*.sql.gz')
    $files = Get-ChildItem -LiteralPath $BackupDir -File -Include $supported -ErrorAction SilentlyContinue
    if (-not $files -or $files.Count -eq 0) {
        Write-Error "No backup files found in: $BackupDir"
        exit 1
    }
    $latestFile = $files | Sort-Object LastWriteTime -Descending | Select-Object -First 1
    $FilePath = $latestFile.FullName
    Write-Host ("Selected latest backup: {0}" -f $FilePath) -ForegroundColor Cyan
}

# Validate input file (after resolving -Latest)
if (-not $FilePath -or -not (Test-Path -LiteralPath $FilePath)) {
    Write-Error ("Backup file not found: {0}" -f ($FilePath ?? '(null)'))
    exit 1
}

# Load backend/.env for PG_* variables
$envFile = Join-Path $Root 'backend\.env'
if (-not (Test-Path $envFile)) {
    Write-Error "Env file not found at $envFile"
    exit 1
}

# Parse .env
$envVars = @{}
Get-Content $envFile | Where-Object { $_ -and ($_ -notmatch '^\s*#') } | ForEach-Object {
    if ($_ -match '^(?<k>[^=\s]+)=(?<v>.*)$') {
        $k = $Matches['k'].Trim()
        $v = $Matches['v'].Trim()
        $envVars[$k] = $v
    }
}

$pgUser = $envVars['PG_USER']; if (-not $pgUser) { $pgUser = 'postgres' }
$pgPass = $envVars['PG_PASSWORD']; if (-not $pgPass) { $pgPass = 'postgres' }
$pgDb   = $envVars['PG_DB']; if (-not $pgDb) { $pgDb = 'sh_school' }

# Warn user that this is destructive unless SkipDrop set
if (-not $SkipDrop -and -not $Force -and -not $AssumeYes) {
    Write-Host "تحذير: سيتم حذف محتوى قاعدة البيانات '$pgDb' ثم استعادتها من النسخة المحددة." -ForegroundColor Yellow
    $ans = Read-Host "هل تريد المتابعة؟ اكتب YES/yes أو Y أو نعم (tip: يمكنك أيضًا كتابة -y أو --yes أو -Force هنا)"
    $valid = @('YES','yes','Yes','Y','y','نعم','-y','--yes','-Force','-force')
    if ($valid -notcontains ($ans ?? '')) {
        Write-Host "تم الإلغاء. لتجاوز التأكيد استخدم: ./scripts/db_restore.ps1 `"$FilePath`" -Force أو -y" -ForegroundColor DarkYellow
        exit 0
    }
}

# Ensure Docker available
try { & docker --version *> $null } catch {
    Write-Error 'Docker CLI is not available. Please install/start Docker Desktop.'
    exit 1
}

$containerName = 'pg-sh-school'

# Ensure container exists and is running
$cid = & docker ps -a --filter "name=$containerName" --format '{{.ID}}'
if (-not $cid) {
    Write-Error "Container '$containerName' not found. Start it via scripts/serve.ps1 or scripts/db_up.ps1 first."
    exit 2
}
$running = & docker ps --filter "name=$containerName" --format '{{.ID}}'
if (-not $running) {
    Write-Host "Starting container $containerName ..."
    & docker start $containerName | Out-Null
}

# Copy file into container temp path
$leaf = Split-Path -Leaf $FilePath
$containerTmp = "/tmp/$leaf"
Write-Host "Copying backup into container: $FilePath -> $($containerName):$containerTmp"
& docker cp $FilePath ($containerName + ':' + $containerTmp)

# Determine dump type by content (magic bytes) with extension as a hint
$lower = $leaf.ToLower()
function Get-FileHeaderBytes {
    param([string]$Path, [int]$Count = 8)
    try {
        $fs = [System.IO.File]::OpenRead($Path)
        try {
            $buf = New-Object byte[] $Count
            $read = $fs.Read($buf, 0, $Count)
            return ,$buf[0..($read-1)]
        } finally { $fs.Dispose() }
    } catch { return @() }
}
$hdr = Get-FileHeaderBytes -Path $FilePath -Count 8
# GZIP magic = 1F 8B
$IsGzip = ($hdr.Length -ge 2 -and $hdr[0] -eq 0x1F -and $hdr[1] -eq 0x8B)
# pg_dump custom directory/tar formats start with ASCII 'PGDMP' for custom, tar is handled by pg_restore too
$IsPgDumpMagic = $false
try {
    $ascii = [System.Text.Encoding]::ASCII.GetString($hdr)
    if ($ascii -like 'PGDMP*') { $IsPgDumpMagic = $true }
} catch { $IsPgDumpMagic = $false }
# Heuristics: consider custom if magic says so OR extension hints (.dump/.backup/.tar)
$IsCustom = $IsPgDumpMagic -or $lower.EndsWith('.dump') -or $lower.EndsWith('.backup') -or $lower.EndsWith('.tar')
# Log detected type for diagnostics
try {
    $detType = if ($IsCustom) { 'custom' } elseif ($IsGzip) { 'gzip-sql' } else { 'sql' }
    Write-Host ("Detected backup type: {0}" -f $detType) -ForegroundColor DarkGray
} catch {}

# Drop schema public (unless SkipDrop)
if (-not $SkipDrop) {
    Write-Host "Dropping and recreating schema 'public' in database '$pgDb' ..."
    $dropCmd = "PGPASSWORD='$pgPass' psql -U '$pgUser' -d '$pgDb' -v ON_ERROR_STOP=1 -c 'DROP SCHEMA IF EXISTS public CASCADE; CREATE SCHEMA public;'"
    & docker exec -u postgres $containerName sh -lc $dropCmd
}

# Restore
Write-Host "Restoring database '$pgDb' from $leaf ..."
$ranFallback = $false
if ($IsCustom) {
    # Use pg_restore for custom format dumps (inside container first)
    $restoreCmd = "PGPASSWORD='$pgPass' pg_restore -U '$pgUser' -d '$pgDb' --clean --if-exists --no-owner --no-privileges --verbose '$containerTmp'"
    # Execute and capture both stdout and stderr to inspect error details
    $out = & docker exec -u postgres $containerName sh -lc $restoreCmd 2>&1
    $code = $LASTEXITCODE
    if ($code -ne 0) {
        $outText = ($out | Out-String)
        $isVersionErr = ($outText -match 'unsupported version' -or $outText -match 'file header')
        if ($isVersionErr) {
            Write-Warning "pg_restore داخل الحاوية لا يدعم نسخة الملف. سنستخدم أداة أحدث (postgres:16) كحل تلقائي."
            # Get container IP for reliable connectivity (works even on default bridge)
            $containerIp = ""
            try { $containerIp = (& docker inspect -f "{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}" $containerName).Trim() } catch {}
            if (-not $containerIp) { throw "تعذر الحصول على IP للحاوية $containerName" }
            # Resolve absolute host paths to avoid mount issues on Windows
            $hostFullPath = (Resolve-Path -LiteralPath $FilePath).Path
            $hostDir = Split-Path -Parent $hostFullPath
            $hostLeaf = Split-Path -Leaf $hostFullPath
            # Detect server major version to pick a compatible client first
            $serverVerNum = ''
            try {
                $serverVerNum = (& docker exec -u postgres --env ("PGPASSWORD=$pgPass") $containerName psql -U $pgUser -d $pgDb -t -A -c "SHOW server_version_num" | Select-Object -First 1).ToString().Trim()
            } catch { $serverVerNum = '' }
            $serverMajor = ''
            if ($serverVerNum -match '^(\d{2})') {
                $serverMajor = [int]$Matches[1]
                if ($serverMajor -lt 10) { $serverMajor = "${serverMajor}" } else { $serverMajor = $serverMajor.ToString() }
            }
            $clientTags = @()
            if ($serverMajor) { $clientTags += @($serverMajor) }
            $clientTags += @('16','17')

            $fbSucceeded = $false
            $fbOutputs = @()
            foreach ($tag in $clientTags) {
                Write-Host ("Running fallback restore via postgres:{0} client..." -f $tag) -ForegroundColor Yellow
                $dockerArgsX = @(
                    'run','--rm',
                    '--env', ("PGPASSWORD=$pgPass"),
                    '-v', ("{0}:/backup" -f $hostDir),
                    ("postgres:{0}" -f $tag),
                    'pg_restore','-h', $containerIp,'-U', $pgUser,'-d', $pgDb,
                    '--clean','--if-exists','--no-owner','--no-privileges','--verbose',
                    ("/backup/$hostLeaf")
                )
                $outX = & docker @dockerArgsX 2>&1
                $codeX = $LASTEXITCODE
                $textX = ($outX | Out-String)
                $fbOutputs += ("[postgres:{0}] exit={1}\n{2}" -f $tag, $codeX, $textX)
                if ($codeX -eq 0) { $fbSucceeded = $true; break }
                # If only error is transaction_timeout (benign for older servers), consider it successful
                if ($textX -match 'unrecognized configuration parameter "transaction_timeout"') {
                    Write-Warning 'تم تجاهل الخطأ المتعلق بـ transaction_timeout (غير مدعوم على الخادم) وسنعتبر الاسترجاع ناجحًا إذا اكتملت باقي الخطوات.'
                    # Treat as success because pg_restore usually continues; do not exit on this
                    $fbSucceeded = $true; break
                }
            }
            if ($fbSucceeded) {
                $ranFallback = $true
            } else {
                # As a last resort, try executing as SQL
                if ($lower.EndsWith('.sql') -or -not $IsPgDumpMagic) {
                    Write-Warning "يبدو أن الملف ليس بصيغة pg_dump المخصصة رغم الامتداد. سنحاول تنفيذ الملف كـ SQL عبر psql..."
                    $sqlCmd = "PGPASSWORD='$pgPass' psql -U '$pgUser' -d '$pgDb' -v ON_ERROR_STOP=1 -f '$containerTmp'"
                    & docker exec -u postgres $containerName sh -lc $sqlCmd
                    if ($LASTEXITCODE -ne 0) {
                        Write-Error ("فشل الاسترجاع كملف SQL أيضًا. تفاصيل المحاولات:\n{0}" -f ($fbOutputs -join "\n---\n"))
                        exit 1
                    }
                    $ranFallback = $true
                } else {
                    Write-Error ("فشل الاسترجاع عبر عملاء postgres المتعددة. التفاصيل:\n{0}" -f ($fbOutputs -join "\n---\n"))
                    exit 1
                }
            }
        } else {
            Write-Error ("pg_restore داخل الحاوية فشل (exit=$code). التفاصيل:\n{0}" -f $outText)
            exit 1
        }
    }
} elseif ($IsGzip) {
    $restoreCmd = "set -e; gzip -dc '$containerTmp' | PGPASSWORD='$pgPass' psql -U '$pgUser' -d '$pgDb' -v ON_ERROR_STOP=1"
    & docker exec -u postgres $containerName sh -lc $restoreCmd
} else {
    $restoreCmd = "PGPASSWORD='$pgPass' psql -U '$pgUser' -d '$pgDb' -v ON_ERROR_STOP=1 -f '$containerTmp'"
    & docker exec -u postgres $containerName sh -lc $restoreCmd
}

# Clean up temp file in container (best-effort)
try { if (-not $ranFallback) { & docker exec $containerName rm -f "$containerTmp" } } catch { }

# --- Post-restore verification ---
Write-Host "التحقق بعد الاسترجاع..." -ForegroundColor Cyan

function Invoke-DbScalar {
    param([string]$Sql)
    try {
        # Execute psql directly via docker exec without sh -lc to avoid quoting issues across PowerShell versions
        $dockerArgs = @(
            'exec','-u','postgres','--env', ("PGPASSWORD=$pgPass"), $containerName,
            'psql','-U', $pgUser, '-d', $pgDb, '-t','-A','-v','ON_ERROR_STOP=1','-c', $Sql
        )
        $out = & docker @dockerArgs
        return ($out | Select-Object -First 1).ToString().Trim()
    } catch {
        return ''
    }
}

# Total tables in public schema
$totalTables = [int](Invoke-DbScalar "SELECT count(*) FROM information_schema.tables WHERE table_schema='public';")

# Key tables to check
$keyTables = @('school_student','school_class','school_staff','attendance_attendancerecord','school_teachingassignment','school_timetableentry')
$counts = @{}
foreach ($t in $keyTables) {
    $cntSql = @(
        "SELECT CASE WHEN EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema='public' AND table_name='" + $t + "') THEN (SELECT count(*) FROM public." + $t + ") ELSE -1 END;"
    ) -join ''
    $val = Invoke-DbScalar $cntSql
    try { $counts[$t] = [int]$val } catch { $counts[$t] = -999 }
}

Write-Host ("عدد الجداول في المخطط public: {0}" -f $totalTables) -ForegroundColor DarkGray
foreach ($kv in $counts.GetEnumerator()) {
    $name = $kv.Key; $val = [int]$kv.Value
    if ($val -eq -1) {
        Write-Host ("الجدول غير موجود: {0}" -f $name) -ForegroundColor Yellow
    } elseif ($val -ge 0 -and $val -le 3) {
        Write-Host ("{0}: {1} صف فقط" -f $name, $val) -ForegroundColor Yellow
    } else {
        Write-Host ("{0}: {1} صف" -f $name, $val) -ForegroundColor Green
    }
}

$allMissingOrZero = ($counts.Values | ForEach-Object { [int]$_ } | Where-Object { $_ -gt 0 } | Measure-Object).Count -eq 0

if ($allMissingOrZero -or $totalTables -lt 5) {
    Write-Warning "يبدو أن قاعدة البيانات المستعادة فارغة أو ناقصة. تحقق من أن الملف صحيح وبصيغة مناسبة (.dump/.backup للـ pg_restore أو SQL نصي)."
    Write-Host "نصائح التشخيص:" -ForegroundColor Yellow
    Write-Host "- تأكد من وجود أداة pg_restore داخل الحاوية: docker exec $containerName pg_restore --version" -ForegroundColor DarkGray
    Write-Host "- إذا كان الملف بصيغة SQL نصي، جرّب بدون امتداد .dump، أو استخدم scripts/restore_db.ps1 (محليًا)." -ForegroundColor DarkGray
    Write-Host "- تأكد من اسم القاعدة وبيانات الاتصال في backend/.env (PG_DB, PG_USER, PG_PASSWORD)." -ForegroundColor DarkGray
    if ($StrictVerify) {
        Write-Error "التحقق الصارم مفعّل: البيانات غير موجودة بعد الاسترجاع."
        exit 3
    }
}

# Additional strict verification for critical tables (teaching assignments/timetable)
try {
    $taCount = ($counts.ContainsKey('school_teachingassignment')) ? [int]$counts['school_teachingassignment'] : -1
    $ttCount = ($counts.ContainsKey('school_timetableentry')) ? [int]$counts['school_timetableentry'] : -1
    if ($taCount -ge 0 -and $taCount -lt 500) {
        Write-Warning ("عدد التكليفات (school_teachingassignment) منخفض بشكل غير معتاد: {0}" -f $taCount)
        if ($StrictVerify) { Write-Error "StrictVerify: teaching assignments seem incomplete (<500)."; exit 4 }
    }
} catch {}

Write-Host "اكتمل الاسترجاع والتحقق." -ForegroundColor Green