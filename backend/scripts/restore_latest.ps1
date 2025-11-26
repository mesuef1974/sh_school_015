#requires -Version 5.1
<#!
Thin wrapper to allow running from backend directory:
  pwsh -File scripts/restore_latest.ps1 [args]

It forwards to the repository root script scripts\restore_latest.ps1.
!#>
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

try {
  # Repo root = backend/.. (two levels up from this file)
  $RepoRoot = Resolve-Path (Join-Path $PSScriptRoot '..\..')
  $Target = Join-Path $RepoRoot 'scripts\restore_latest.ps1'
  if (-not (Test-Path -LiteralPath $Target)) {
    Write-Error "Cannot find root restore script at $Target"
    exit 1
  }
  & pwsh -File $Target @args
  exit $LASTEXITCODE
} catch {
  Write-Error $_
  exit 1
}
