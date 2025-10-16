#requires -Version 5.1
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

<#
PostgreSQL helpers for this project (Windows PowerShell)

Purpose
- Avoid "what is the password?" and wrong port issues by reading backend/.env.
- Provide easy commands to backup/restore DB and enable extensions.

Usage examples (run from project root or any location):
  # Load the functions into your session
  PS> . ./scripts/pg_helpers.ps1

  # Show resolved connection info (from backend/.env)
  PS> Show-DbEnv

  # Quick connection test
  PS> Test-DbConnection

  # Create the database if missing
  PS> Create-DbIfMissing

  # Backup (custom format .dump) to backups/ with timestamp
  PS> Backup-Db

  # Restore from a .dump (will drop/clean target objects)
  PS> Restore-Db -DumpPath .\backups\backup_sh_school_2025-10-15_1855.dump

  # Enable pg_trgm extension (if not already)
  PS> Enable-Trgm

Notes
- Requires PostgreSQL client tools (psql, pg_dump, pg_restore) in PATH.
- Values are read from backend/.env: PG_HOST, PG_PORT, PG_DB, PG_USER, PG_PASSWORD.
- This script only helps your local/dev usage; it does not alter Django settings.
#>

# Resolve project root and .env path
try {
  $ScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
  $ProjectRoot = Resolve-Path (Join-Path $ScriptRoot '..')
} catch { $ProjectRoot = (Get-Location).Path }
$EnvPath = Join-Path $ProjectRoot 'backend\.env'

# Parse backend/.env (simple key=value, ignore comments)
$DbEnv = @{}
if (Test-Path -Path $EnvPath) {
  try {
    Get-Content $EnvPath | Where-Object { $_ -and ($_ -notmatch '^[\s#]') } | ForEach-Object {
      if ($_ -match '^(?<k>[^=\s]+)=(?<v>.*)$') {
        $key = $Matches['k'].Trim()
        $val = $Matches['v']
        # Trim whitespace first
        $val = $val.Trim()
        # If value is not quoted, strip inline comments starting with '#'
        if ($val.Length -gt 0 -and $val[0] -ne '"' -and $val[0] -ne "'") {
          $hashIndex = $val.IndexOf('#')
          if ($hashIndex -ge 0) { $val = $val.Substring(0, $hashIndex).Trim() }
        }
        # Remove surrounding quotes if present
        if (($val.StartsWith('"') -and $val.EndsWith('"')) -or ($val.StartsWith("'") -and $val.EndsWith("'"))) {
          if ($val.Length -ge 2) { $val = $val.Substring(1, $val.Length - 2) }
        }
        $DbEnv[$key] = $val
      }
    }
  } catch {
    Write-Warning "Failed to read .env: $($_.Exception.Message)"
  }
}

function Get-DbConfig {
  $pgHost = $DbEnv['PG_HOST']; if (-not $pgHost) { $pgHost = '127.0.0.1' }
  $pgPort = $DbEnv['PG_PORT']; if (-not $pgPort) { $pgPort = '5432' }
  $pgDb   = $DbEnv['PG_DB'];   if (-not $pgDb)   { $pgDb   = 'sh_school' }
  $pgUser = $DbEnv['PG_USER']; if (-not $pgUser) { $pgUser = 'postgres' }
  $pgPass = $DbEnv['PG_PASSWORD']; if (-not $pgPass) { $pgPass = '' }
  [pscustomobject]@{ Host=$pgHost; Port=$pgPort; Db=$pgDb; User=$pgUser; Password=$pgPass }
}

function Show-DbEnv {
  [CmdletBinding()] param()
  $cfg = Get-DbConfig
  Write-Host ("Host: {0}" -f $cfg.Host)
  Write-Host ("Port: {0}" -f $cfg.Port)
  Write-Host ("DB:   {0}" -f $cfg.Db)
  Write-Host ("User: {0}" -f $cfg.User)
  if ($cfg.Password) { Write-Host "Password: (from .env)" } else { Write-Host "Password: (empty or not set)" }
}

function Invoke-PsqlCommand {
  param(
    [Parameter(Mandatory=$true)][string]$Sql,
    [string]$DbName
  )
  $cfg = Get-DbConfig
  $env:PGPASSWORD = $cfg.Password
  try {
    $args = @('-h', $cfg.Host, '-p', "$($cfg.Port)", '-U', $cfg.User)
    if ($DbName) { $args += @('-d', $DbName) } else { $args += @('-d', $cfg.Db) }
    $args += @('-c', $Sql)
    & psql @args
    if ($LASTEXITCODE -ne 0) { throw "psql exited with code $LASTEXITCODE" }
  } finally {
    Remove-Item Env:PGPASSWORD -ErrorAction SilentlyContinue | Out-Null
  }
}

function Test-DbConnection {
  [CmdletBinding()] param()
  $cfg = Get-DbConfig
  Write-Host ("Testing connection to {0}:{1}/{2} as {3} ..." -f $cfg.Host,$cfg.Port,$cfg.Db,$cfg.User) -ForegroundColor Cyan
  try {
    Invoke-PsqlCommand -Sql 'SELECT current_database(), current_user, version();' | Out-Null
    Write-Host "OK" -ForegroundColor Green
  } catch {
    Write-Warning $_
    Write-Host "Tip: Check backend/.env values. This project uses port 5433 by default." -ForegroundColor Yellow
  }
}

function Create-DbIfMissing {
  [CmdletBinding()] param()
  $cfg = Get-DbConfig
  Write-Host ("Ensuring database '{0}' exists on {1}:{2} ..." -f $cfg.Db,$cfg.Host,$cfg.Port)
  $env:PGPASSWORD = $cfg.Password
  try {
    # Query postgres catalog via default 'postgres' DB to avoid failure if target db absent
    $args = @('-h', $cfg.Host, '-p', "$($cfg.Port)", '-U', $cfg.User, '-d', 'postgres', '-t', '-A', '-c', "SELECT 1 FROM pg_database WHERE datname = '$($cfg.Db)'")
    $out = & psql @args
    if ($LASTEXITCODE -ne 0) { throw "psql exited with code $LASTEXITCODE" }
    if ($out -match '^1$') {
      Write-Host "Database already exists."
    } else {
      Write-Host "Creating database ..."
      Invoke-PsqlCommand -DbName 'postgres' -Sql ("CREATE DATABASE `"$($cfg.Db)`";")
      Write-Host "Created." -ForegroundColor Green
    }
  } finally {
    Remove-Item Env:PGPASSWORD -ErrorAction SilentlyContinue | Out-Null
  }
}

function Backup-Db {
  [CmdletBinding()] param(
    [string]$OutDir
  )
  $cfg = Get-DbConfig
  if (-not $OutDir) { $OutDir = Join-Path $ProjectRoot 'backups' }
  if (-not (Test-Path -Path $OutDir)) { New-Item -ItemType Directory -Path $OutDir | Out-Null }
  $ts = Get-Date -Format 'yyyy-MM-dd_HHmm'
  $file = Join-Path $OutDir ("backup_{0}_{1}.dump" -f $cfg.Db,$ts)
  Write-Host ("Backing up to {0}" -f $file) -ForegroundColor Cyan
  $env:PGPASSWORD = $cfg.Password
  try {
    & pg_dump -h $cfg.Host -p "$($cfg.Port)" -U $cfg.User -d $cfg.Db -Fc -f $file
    if ($LASTEXITCODE -ne 0) { throw "pg_dump exited with code $LASTEXITCODE" }
    Write-Host "Backup completed." -ForegroundColor Green
    return $file
  } finally {
    Remove-Item Env:PGPASSWORD -ErrorAction SilentlyContinue | Out-Null
  }
}

function Restore-Db {
  [CmdletBinding()] param(
    [Parameter(Mandatory=$true)][string]$DumpPath
  )
  if (-not (Test-Path -Path $DumpPath)) { throw "Dump file not found: $DumpPath" }
  $cfg = Get-DbConfig
  $env:PGPASSWORD = $cfg.Password
  try {
    Write-Host ("Restoring {0} into {1} ..." -f $DumpPath,$cfg.Db) -ForegroundColor Yellow
    & pg_restore -h $cfg.Host -p "$($cfg.Port)" -U $cfg.User -d $cfg.Db --clean "$DumpPath"
    if ($LASTEXITCODE -ne 0) { throw "pg_restore exited with code $LASTEXITCODE" }
    Write-Host "Restore completed." -ForegroundColor Green
  } finally {
    Remove-Item Env:PGPASSWORD -ErrorAction SilentlyContinue | Out-Null
  }
}

function Enable-Trgm {
  [CmdletBinding()] param()
  Write-Host "Enabling extension pg_trgm (if not exists) ..."
  Invoke-PsqlCommand -Sql 'CREATE EXTENSION IF NOT EXISTS pg_trgm;'
}

function Test-IndexExists {
  [CmdletBinding()] param(
    [Parameter(Mandatory=$true)][string]$IndexName,
    [string]$Schema = 'public'
  )
  $cfg = Get-DbConfig
  $env:PGPASSWORD = $cfg.Password
  try {
    $sql = @"
SELECT 1
FROM pg_class i
JOIN pg_namespace n ON n.oid = i.relnamespace
WHERE i.relkind = 'i'
  AND i.relname = '$IndexName'
  AND n.nspname = '$Schema';
"@
    $args = @('-h', $cfg.Host, '-p', "$($cfg.Port)", '-U', $cfg.User, '-d', $cfg.Db, '-t', '-A', '-c', $sql)
    $out = & psql @args
    if ($LASTEXITCODE -ne 0) { throw "psql exited with code $LASTEXITCODE" }
    return ($out -match '^1$')
  } finally {
    Remove-Item Env:PGPASSWORD -ErrorAction SilentlyContinue | Out-Null
  }
}

function Ensure-TrgmIndex {
  [CmdletBinding()] param(
    [string]$Table = 'school_student',
    [string]$Column = 'full_name',
    [string]$IndexName = 'student_name_trgm',
    [string]$Schema = 'public'
  )
  # Ensure extension exists first
  Enable-Trgm
  if (Test-IndexExists -IndexName $IndexName -Schema $Schema) {
    Write-Host ("Index '{0}' already exists." -f $IndexName)
    return
  }
  $qualifiedTable = if ($Schema) { '"' + $Schema + '"."' + $Table + '"' } else { '"' + $Table + '"' }
  $qualifiedIndex = '"' + $IndexName + '"'
  $qualifiedColumn = '"' + $Column + '"'
  $sql = "CREATE INDEX CONCURRENTLY $qualifiedIndex ON $qualifiedTable USING GIN ($qualifiedColumn gin_trgm_ops);"
  Write-Host ("Creating GIN trigram index '{0}' on {1}({2}) ..." -f $IndexName, $Table, $Column) -ForegroundColor Cyan
  try {
    Invoke-PsqlCommand -Sql $sql
    Write-Host "Index created." -ForegroundColor Green
  } catch {
    Write-Warning ("Failed to create index: {0}" -f $_.Exception.Message)
    Write-Host "Tip: Make sure no other session is running a concurrent index build with the same name." -ForegroundColor DarkYellow
    throw
  }
}