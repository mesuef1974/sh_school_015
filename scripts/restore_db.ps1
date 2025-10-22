#requires -Version 5.1
param(
  [Parameter(Mandatory = $true)] [string]$Dump,
  [string]$Db = 'sh_school',
  [string]$User = 'postgres',
  [string]$Host = 'localhost',
  [int]$Port = 5432,
  [string]$Password
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# Resolve absolute path for the dump
$DumpPath = Resolve-Path -LiteralPath $Dump | ForEach-Object { $_.Path }
if (-not (Test-Path -LiteralPath $DumpPath)) {
  throw "File not found: $Dump"
}

# Export password for libpq tools if provided
if ($Password) { $Env:PGPASSWORD = $Password }

function Test-Cli {
  param([string]$Name)
  try { return [bool](Get-Command $Name -ErrorAction Stop) } catch { return $false }
}

# Try to locate PostgreSQL bin tools if not on PATH
if (-not (Test-Cli 'psql')) {
  $commonPaths = @(
    'C:\Program Files\PostgreSQL\16\bin',
    'C:\Program Files\PostgreSQL\15\bin',
    'C:\Program Files\PostgreSQL\14\bin'
  )
  foreach ($p in $commonPaths) {
    if (Test-Path $p) {
      $env:PATH = "$p;" + $env:PATH
      break
    }
  }
}

if (-not (Test-Cli 'psql')) { throw 'psql was not found on PATH. Install PostgreSQL client tools.' }
if (-not (Test-Cli 'pg_restore')) { Write-Verbose 'pg_restore not found; .dump will fail unless psql SQL is used.' }

Write-Host "Restoring database '$Db' from: $DumpPath" -ForegroundColor Cyan

# Drop connections and recreate database
Write-Host 'Terminating connections...' -ForegroundColor DarkGray
psql -h $Host -p $Port -U $User -d postgres -v ON_ERROR_STOP=1 -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '$Db' AND pid <> pg_backend_pid();" | Out-Null

Write-Host 'Dropping database (if exists)...' -ForegroundColor DarkGray
psql -h $Host -p $Port -U $User -d postgres -v ON_ERROR_STOP=1 -c "DROP DATABASE IF EXISTS \"$Db\";" | Out-Null

Write-Host 'Creating database...' -ForegroundColor DarkGray
psql -h $Host -p $Port -U $User -d postgres -v ON_ERROR_STOP=1 -c "CREATE DATABASE \"$Db\" WITH ENCODING 'UTF8' TEMPLATE template0;" | Out-Null

# Decide restore method by extension (best-effort)
$ext = [System.IO.Path]::GetExtension($DumpPath).ToLowerInvariant()
$usePgRestore = $ext -in @('.dump', '.dmp', '.backup', '.tar')

if ($usePgRestore) {
  if (-not (Test-Cli 'pg_restore')) { throw 'pg_restore not found, but a custom-format dump was provided.' }
  Write-Host 'Using pg_restore (custom format)...' -ForegroundColor Yellow
  & pg_restore -h $Host -p $Port -U $User -d $Db --clean --if-exists --no-owner --no-privileges --verbose --single-transaction --exit-on-error --disable-triggers "$DumpPath"
} else {
  Write-Host 'Using psql to execute SQL file...' -ForegroundColor Yellow
  & psql -h $Host -p $Port -U $User -d $Db -v ON_ERROR_STOP=1 -f "$DumpPath"
}

Write-Host 'Verifying tables...' -ForegroundColor DarkGray
psql -h $Host -p $Port -U $User -d $Db -c "\\dt" | Out-Null

Write-Host 'Restore completed successfully.' -ForegroundColor Green