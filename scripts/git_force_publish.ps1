#requires -Version 5.1
<#!
.SYNOPSIS
  Force-publish the project to GitHub using professional, safe defaults.

.DESCRIPTION
  This PowerShell script initializes Git if needed, prepares a professional .gitignore,
  optionally configures Git LFS for binary assets, commits all tracked files, sets the remote,
  and pushes to GitHub. It supports a force push option using --force-with-lease.

.PARAMETER Remote
  The Git remote URL (e.g., https://github.com/ORG/REPO.git or git@github.com:ORG/REPO.git).

.PARAMETER Branch
  Target branch name (default: main).

.PARAMETER Force
  If supplied, push with --force-with-lease (safer than --force) to overwrite remote history.

.PARAMETER IncludeBackups
  Include the backups/ folder in the commit (default: excluded). Use this only if desired.

.PARAMETER IncludeLFS
  Configure Git LFS and track common binary types (png/jpg/pdf/xlsx/docx/pptx/zip, etc.).

.PARAMETER PushTags
  Also push tags to the remote.

.PARAMETER DryRun
  Show what would be done without executing push/remote changes.

.EXAMPLE
  pwsh -File scripts/git_force_publish.ps1 -Remote "git@github.com:myorg/sh_school_015.git"

.EXAMPLE
  pwsh -File scripts/git_force_publish.ps1 -Remote "https://github.com/myorg/sh_school_015.git" -Branch main -Force -IncludeLFS

.NOTES
  - Ensure you are authenticated with GitHub (SSH key or HTTPS credentials/cached login).
  - Use Force only when you intend to overwrite the remote branch history.
#>
param(
  [Parameter(Mandatory=$true)][string]$Remote,
  [string]$Branch = 'main',
  [switch]$Force,
  [switch]$IncludeBackups,
  [switch]$IncludeLFS,
  [switch]$PushTags,
  [switch]$DryRun
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# Move to project root (parent of this script directory)
$Root = Resolve-Path (Join-Path $PSScriptRoot '..')
Set-Location $Root

function Write-Step($msg){ Write-Host "[STEP] $msg" -ForegroundColor Cyan }
function Write-Warn($msg){ Write-Host "[WARN] $msg" -ForegroundColor Yellow }
function Write-Info($msg){ Write-Host "[INFO] $msg" -ForegroundColor DarkGray }
function Write-Ok($msg){ Write-Host "[OK] $msg" -ForegroundColor Green }

# 1) Check for git
try {
  git --version | Out-Null
} catch {
  throw "Git is not installed or not available in PATH. Please install Git (https://git-scm.com/downloads)."
}

# 2) Initialize repo if missing
$gitDir = Join-Path $Root '.git'
if (-not (Test-Path $gitDir)) {
  Write-Step "Initializing new Git repository"
  if (-not $DryRun) { git init | Out-Null }
} else {
  Write-Info "Git repository already initialized"
}

# 3) Ensure professional .gitignore
$gitignorePath = Join-Path $Root '.gitignore'
$defaultIgnore = @'
# Python
__pycache__/
*.py[cod]
*$py.class

# Environments
.venv/
.env
backend/.env

# Django
*.sqlite3
staticfiles/
media/

# OS/Tools
.DS_Store
Thumbs.db
.idea/
.vscode/
*.log

# Node (if any)
node_modules/

# Backups (excluded by default)
backups/

# Compiled/archives
*.zip
*.tar
*.tar.gz
*.rar

# Reports/exports (optional)
*.xlsx
*.xlsm
*.pdf

'@

if (-not (Test-Path $gitignorePath)) {
  Write-Step "Creating .gitignore"
  if (-not $DryRun) { $defaultIgnore | Out-File -FilePath $gitignorePath -Encoding UTF8 -Force }
} else {
  # Merge minimal must-have ignores if missing
  $existing = Get-Content $gitignorePath -ErrorAction SilentlyContinue
  $linesToEnsure = @('.venv/','__pycache__/','*.py[cod]','backend/.env','backups/')
  $missing = @()
  foreach ($l in $linesToEnsure) { if ($existing -notcontains $l) { $missing += $l } }
  if ($missing.Count -gt 0) {
    Write-Step "Updating .gitignore with essential entries: $($missing -join ', ')"
    if (-not $DryRun) { Add-Content -Path $gitignorePath -Value ($missing -join "`n") }
  } else {
    Write-Info ".gitignore already has essential entries"
  }
}

# Optionally include backups
if ($IncludeBackups) {
  Write-Warn "Including backups/ in commit as requested. This may produce very large pushes."
  # Remove 'backups/' from .gitignore if present
  if (-not $DryRun) {
    $gi = Get-Content $gitignorePath -ErrorAction SilentlyContinue
    if ($gi) {
      $newGi = $gi | Where-Object { $_ -ne 'backups/' }
      $newGi | Set-Content -Path $gitignorePath -Encoding UTF8
    }
  }
}

# 4) Optionally configure Git LFS
if ($IncludeLFS) {
  Write-Step "Configuring Git LFS (if available)"
  $hasLfs = $true
  try { git lfs version | Out-Null } catch { $hasLfs = $false }
  if ($hasLfs) {
    if (-not $DryRun) {
      git lfs install | Out-Null
      # Common binary patterns
      $patterns = @('*.png','*.jpg','*.jpeg','*.gif','*.webp','*.svg','*.pdf','*.xlsx','*.xlsm','*.docx','*.pptx','*.zip','*.rar')
      foreach ($p in $patterns) { git lfs track $p | Out-Null }
      git add .gitattributes | Out-Null
    }
    Write-Ok "Git LFS configured"
  } else {
    Write-Warn "git-lfs not found; skipping LFS configuration. Install from https://git-lfs.com/ if needed."
  }
}

# 5) Ensure default branch exists and is checked out
try {
  $currentBranch = (git rev-parse --abbrev-ref HEAD).Trim()
} catch { $currentBranch = '' }
if (-not $currentBranch -or $currentBranch -eq 'HEAD') {
  Write-Step "Creating and switching to branch '$Branch'"
  if (-not $DryRun) { git checkout -B $Branch | Out-Null }
} elseif ($currentBranch -ne $Branch) {
  Write-Step "Switching to branch '$Branch' (from '$currentBranch')"
  if (-not $DryRun) { git checkout -B $Branch | Out-Null }
}

# 6) Add and commit
Write-Step "Staging changes"
if (-not $DryRun) { git add -A }

# Generate commit message with timestamp
$ts = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
$commitMsg = "Publish: automated snapshot ($ts)"

# Only commit if there is anything to commit
$hasChanges = $true
try {
  $status = git status --porcelain
  $hasChanges = -not [string]::IsNullOrWhiteSpace($status)
} catch { $hasChanges = $true }

if ($hasChanges) {
  Write-Step "Committing changes"
  if (-not $DryRun) { git commit -m $commitMsg | Out-Null }
} else {
  Write-Info "No changes to commit"
}

# 7) Configure remote
Write-Step "Setting remote 'origin' to $Remote"
if (-not $DryRun) {
  $existingRemote = ''
  try { $existingRemote = (git remote get-url origin) } catch { $existingRemote = '' }
  if ($existingRemote) {
    if ($existingRemote -ne $Remote) { git remote set-url origin $Remote | Out-Null }
  } else {
    git remote add origin $Remote | Out-Null
  }
}

# 8) Push
Write-Step "Pushing to $Remote ($Branch)"
$pushArgs = @('push','-u','origin',$Branch)
if ($Force) { $pushArgs += '--force-with-lease' }

if ($DryRun) {
  Write-Warn "Dry-run enabled: skipping push. Would run: git $($pushArgs -join ' ')"
} else {
  git @pushArgs
  if ($LASTEXITCODE -ne 0) { throw "git push failed with exit code $LASTEXITCODE" }
  Write-Ok "Pushed branch '$Branch' to origin"
}

# 9) Optionally push tags
if ($PushTags) {
  Write-Step "Pushing tags"
  if ($DryRun) {
    Write-Warn "Dry-run: skipping tags push. Would run: git push --tags"
  } else {
    git push --tags
    if ($LASTEXITCODE -ne 0) { throw "git push --tags failed with exit code $LASTEXITCODE" }
    Write-Ok "Tags pushed"
  }
}

Write-Host "\nDone." -ForegroundColor Green
Write-Host "Examples:" -ForegroundColor Gray
Write-Host "  pwsh -File scripts/git_force_publish.ps1 -Remote 'git@github.com:ORG/REPO.git' -Branch main -Force -IncludeLFS" -ForegroundColor Gray
Write-Host "  pwsh -File scripts/git_force_publish.ps1 -Remote 'https://github.com/ORG/REPO.git'" -ForegroundColor Gray