#requires -Version 5.1
<#
  Fix frontend node_modules on Windows (EPERM / locked esbuild.exe)
  Usage (PowerShell as Administrator recommended):

    pwsh -File scripts\fe_fix_nodemodules.ps1
    # Optional: force ownership/ACL reset if needed
    pwsh -File scripts\fe_fix_nodemodules.ps1 -Force

#>
Param(
  [switch]$Force = $false
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# Move to frontend directory
$Root = Resolve-Path (Join-Path $PSScriptRoot '..')
$FeDir = Join-Path $Root 'frontend'
Push-Location $FeDir

try {
  Write-Host '[fe-fix] Stopping leftover Node/Vite/esbuild processes (if any) ...' -ForegroundColor Cyan
  Get-Process node,vite,esbuild -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue

  $esbuildDir = Join-Path $FeDir 'node_modules\@esbuild'
  if (Test-Path $esbuildDir) {
    Write-Host '[fe-fix] Cleaning @esbuild binaries ...' -ForegroundColor Yellow
    try { Remove-Item -LiteralPath $esbuildDir -Recurse -Force -ErrorAction SilentlyContinue } catch {}
  }

  if (Test-Path 'node_modules') {
    Write-Host '[fe-fix] Removing node_modules ...' -ForegroundColor Yellow
    try { Remove-Item -LiteralPath 'node_modules' -Recurse -Force } catch {
      Write-Warning ("[fe-fix] Failed to remove node_modules: {0}" -f $_.Exception.Message)
      if ($Force) {
        Write-Host '[fe-fix] Taking ownership and resetting ACLs (Administrators:F) ...' -ForegroundColor Yellow
        & takeown /F . /A /R | Out-Null
        & icacls . /grant Administrators:F /T | Out-Null
        Remove-Item -LiteralPath 'node_modules' -Recurse -Force
      } else { throw }
    }
  }

  Write-Host '[fe-fix] Running npm ci ...' -ForegroundColor Cyan
  npm ci
  if ($LASTEXITCODE -ne 0) { throw "npm ci failed with exit code $LASTEXITCODE" }
  Write-Host '[fe-fix] Done. Frontend deps reinstalled successfully.' -ForegroundColor Green

} catch {
  Write-Error ("[fe-fix] Error: {0}" -f $_.Exception.Message)
  exit 1
} finally {
  Pop-Location
}
