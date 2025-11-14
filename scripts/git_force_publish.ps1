#requires -Version 5.1
<#
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
  Also push tags to the remote.y

.PARAMETER DryRun
  Show what would be done without executing push/remote changes.

.PARAMETER HttpsFallback
  If an SSH push fails with "Permission denied (publickey)", automatically switch the remote to HTTPS and retry once.

.EXAMPLE
  pwsh -File scripts/git_force_publish.ps1 -Remote "git@github.com:myorg/sh_school_015.git"

.EXAMPLE
  pwsh -File scripts/git_force_publish.ps1 -Remote "https://github.com/myorg/sh_school_015.git" -Branch main -Force -IncludeLFS

.EXAMPLE
  pwsh -File scripts/git_force_publish.ps1 -Remote "git@github.com:myorg/sh_school_015.git" -HttpsFallback

.NOTES
  - Ensure you are authenticated with GitHub (SSH key or HTTPS credentials/cached login).
  - Use Force only when you intend to overwrite the remote branch history.
#>
param(
  [Parameter(Mandatory=$false)][string]$Remote = '',
  [string]$Branch = 'main',
  [switch]$Force,
  [switch]$IncludeBackups,
  [switch]$IncludeLFS,
  [switch]$PushTags,
  [switch]$HttpsFallback,
  [switch]$SkipHooks,
  [switch]$BypassHooksOnFailure,
  [switch]$DryRun
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# Prepare URL patterns for remote validation (used later when resolving -Remote)
$httpPattern = '^(https://|http://).+?/.+?/.+?\.git$'
$sshPattern = '^git@[^:]+:[^/]+/.+?\.git$'
$sshUrlPattern = '^ssh://git@[^/]+/[^/]+/.+?\.git$'

# Move to project root (parent of this script directory)
$Root = Resolve-Path (Join-Path $PSScriptRoot '..')
Set-Location $Root

function Write-Step($msg){ Write-Host "[STEP] $msg" -ForegroundColor Cyan }
function Write-Warn($msg){ Write-Host "[WARN] $msg" -ForegroundColor Yellow }
function Write-Info($msg){ Write-Host "[INFO] $msg" -ForegroundColor DarkGray }
function Write-Ok($msg){ Write-Host "[OK] $msg" -ForegroundColor Green }

function Is-PlaceholderRemote([string]$url) {
  if (-not $url) { return $false }
  # Detect placeholders like ORG/REPO at the end (ssh or https forms)
  return ($url -match '[:/\\]ORG/REPO(\.git)?$')
}

function Prompt-ForRemote([string]$prompt) {
  $answer = Read-Host $prompt
  $ansTrim = ($answer | ForEach-Object { $_.Trim() })
  if ([string]::IsNullOrWhiteSpace($ansTrim)) { return $null }
  if ($ansTrim -match $httpPattern -or $ansTrim -match $sshPattern -or $ansTrim -match $sshUrlPattern) {
    return $ansTrim
  }
  Write-Warn "The provided value does not look like a valid Git URL."
  return $null
}

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
# PythonY
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

# Pre-fix: if a remote accidentally named 'mean' exists, rename it to 'origin' before resolving
try {
  $remotes = (git remote).Trim().Split([Environment]::NewLine) | Where-Object { $_ -ne '' }
} catch { $remotes = @() }
if ($remotes -and ($remotes -contains 'mean') -and -not ($remotes -contains 'origin')) {
  Write-Warn "Detected remote named 'mean'. Renaming it to 'origin'."
  try { git remote rename mean origin | Out-Null } catch { Write-Warn "Failed to rename remote 'mean' to 'origin': $($_.Exception.Message)" }
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
  if (-not $DryRun) {
    $commitArgs = @('commit','-m',$commitMsg)
    if ($SkipHooks) { $commitArgs += '--no-verify' }

    $gitCommitOutput = & git @commitArgs 2>&1
    $commitExit = $LASTEXITCODE
    if ($commitExit -ne 0) {
      Write-Warn "git commit failed. Git output:"
      Write-Host ($gitCommitOutput | Out-String) -ForegroundColor DarkGray

      $looksLikePreCommit = ($gitCommitOutput -match 'pre-commit' -or $gitCommitOutput -match 'An unexpected error has occurred' -or $gitCommitOutput -match 'CalledProcessError')
      $autoBypass = $false
      if ($env:GIT_FORCE_PUBLISH_AUTO_BYPASS) {
        $autoBypass = ($env:GIT_FORCE_PUBLISH_AUTO_BYPASS -match '^(?i:1|true|yes|y)$')
      }

      if (-not $SkipHooks -and $looksLikePreCommit) {
        if ($BypassHooksOnFailure -or $autoBypass) {
          Write-Step "Retrying commit without hooks (--no-verify) due to hook failure"
          $commitArgs += '--no-verify'
          # Hooks like black/ruff may have modified files; re-stage before retrying
          git add -A | Out-Null
          $gitCommitOutput2 = & git @commitArgs 2>&1
          $commitExit2 = $LASTEXITCODE
          if ($commitExit2 -ne 0) {
            $out2 = ($gitCommitOutput2 | Out-String)
            # If there is nothing to commit after hooks formatted files, proceed
            if ($out2 -match '(?i)nothing to commit' -or $out2 -match '(?i)nothing added to commit') {
              Write-Info "No changes to commit after hooks; continuing."
            } else {
              Write-Warn "Retry without hooks also failed. Git output:"
              Write-Host $out2 -ForegroundColor DarkGray
              throw "git commit failed with exit code $commitExit2"
            }
          }
        } else {
          $resp = Read-Host "Commit hooks appear to have failed. Retry without hooks (--no-verify)? [y/N]"
          if ($resp -match '^(?i:y(?:es)?)$') {
            Write-Step "Retrying commit without hooks (--no-verify) per user confirmation"
            $commitArgs += '--no-verify'
            # Hooks may have changed files; re-stage before retrying
            git add -A | Out-Null
            $gitCommitOutput2 = & git @commitArgs 2>&1
            $commitExit2 = $LASTEXITCODE
            if ($commitExit2 -ne 0) {
              $out2 = ($gitCommitOutput2 | Out-String)
              if ($out2 -match '(?i)nothing to commit' -or $out2 -match '(?i)nothing added to commit') {
                Write-Info "No changes to commit after hooks; continuing."
              } else {
                Write-Warn "Retry without hooks also failed. Git output:"
                Write-Host $out2 -ForegroundColor DarkGray
                throw "git commit failed with exit code $commitExit2"
              }
            }
          } else {
            Write-Host "[HINT] If this is caused by a failing hook, you can re-run with -BypassHooksOnFailure or -SkipHooks to proceed without hooks." -ForegroundColor Yellow
            throw "git commit failed with exit code $commitExit"
          }
        }
      } else {
        # If commit failed but there is actually nothing to commit, proceed.
        $out1 = ($gitCommitOutput | Out-String)
        if ($out1 -match '(?i)nothing to commit' -or $out1 -match '(?i)nothing added to commit') {
          Write-Info "No changes to commit; continuing."
        } else {
          Write-Host "[HINT] If this is caused by a failing hook, you can re-run with -BypassHooksOnFailure or -SkipHooks to proceed without hooks." -ForegroundColor Yellow
          throw "git commit failed with exit code $commitExit"
        }
      }
    }
  }
} else {
  Write-Info "No changes to commit"
}

# Resolve remote URL to use (prefer explicit -Remote, else existing origin)
$resolvedRemote = ''
$remoteTrim = ($Remote | ForEach-Object { $_.Trim() })
# Re-check existing origin after potential rename
try { $existingRemote = (git remote get-url origin) } catch { $existingRemote = '' }
if ([string]::IsNullOrWhiteSpace($remoteTrim)) {
  if ($existingRemote) {
    $existingTrim = ($existingRemote | ForEach-Object { $_.Trim() })
    $existingIsCommonMistake = @('main','master','upstream','mean') -contains $existingTrim
    $existingLooksValid = ($existingTrim -match $httpPattern -or $existingTrim -match $sshPattern -or $existingTrim -match $sshUrlPattern)
    if ($existingIsCommonMistake -or -not $existingLooksValid) {
      Write-Warn "Existing remote 'origin' points to '$existingRemote', which is not a valid Git remote URL."
      # Interactive fallback: ask the user to enter a valid remote URL now
      $answer = Read-Host "Enter Git remote URL (e.g., https://github.com/ORG/REPO.git or git@github.com:ORG/REPO.git). Press Enter to cancel"
      $ansTrim = ($answer | ForEach-Object { $_.Trim() })
      if (-not [string]::IsNullOrWhiteSpace($ansTrim)) {
        if ($ansTrim -match $httpPattern -or $ansTrim -match $sshPattern -or $ansTrim -match $sshUrlPattern) {
          $resolvedRemote = $ansTrim
          Write-Info "Using provided remote URL: $resolvedRemote"
        } else {
          Write-Warn "The provided value does not look like a valid Git URL."
          Write-Host "[USAGE] Please provide -Remote with a full Git URL to fix the origin, for example:" -ForegroundColor Yellow
          Write-Host "  pwsh -File scripts/git_force_publish.ps1 -Remote 'git@github.com:ORG/REPO.git' -Branch $Branch" -ForegroundColor Gray
          Write-Host "  pwsh -File scripts/git_force_publish.ps1 -Remote 'https://github.com/ORG/REPO.git'" -ForegroundColor Gray
          Write-Host "Or fix it directly: git remote set-url origin <URL>" -ForegroundColor Gray
          exit 1
        }
      } else {
        Write-Host "[USAGE] Please provide -Remote with a full Git URL to fix the origin, for example:" -ForegroundColor Yellow
        Write-Host "  pwsh -File scripts/git_force_publish.ps1 -Remote 'git@github.com:ORG/REPO.git' -Branch $Branch" -ForegroundColor Gray
        Write-Host "  pwsh -File scripts/git_force_publish.ps1 -Remote 'https://github.com/ORG/REPO.git'" -ForegroundColor Gray
        Write-Host "Or fix it directly: git remote set-url origin <URL>" -ForegroundColor Gray
        exit 1
      }
    } else {
      Write-Info "Using existing remote 'origin': $existingRemote"
      $resolvedRemote = $existingRemote
    }
  } else {
    Write-Warn "No -Remote provided and no existing 'origin' remote is configured."
    # Interactive fallback: ask the user to enter a valid remote URL now
    $answer = Read-Host "Enter Git remote URL (e.g., https://github.com/ORG/REPO.git or git@github.com:ORG/REPO.git). Press Enter to cancel"
    $ansTrim = ($answer | ForEach-Object { $_.Trim() })
    if (-not [string]::IsNullOrWhiteSpace($ansTrim)) {
      if ($ansTrim -match $httpPattern -or $ansTrim -match $sshPattern -or $ansTrim -match $sshUrlPattern) {
        $resolvedRemote = $ansTrim
        Write-Info "Using provided remote URL: $resolvedRemote"
      } else {
        Write-Warn "The provided value does not look like a valid Git URL."
        Write-Host "[USAGE] Provide -Remote with a full Git URL, or configure origin first." -ForegroundColor Yellow
        Write-Host "Examples:" -ForegroundColor Gray
        Write-Host "  pwsh -File scripts/git_force_publish.ps1 -Remote 'git@github.com:ORG/REPO.git' -Branch $Branch" -ForegroundColor Gray
        Write-Host "  pwsh -File scripts/git_force_publish.ps1 -Remote 'https://github.com/ORG/REPO.git'" -ForegroundColor Gray
        Write-Host "Or set origin: git remote add origin <URL>" -ForegroundColor Gray
        exit 1
      }
    } else {
      Write-Host "[USAGE] Provide -Remote with a full Git URL, or configure origin first." -ForegroundColor Yellow
      Write-Host "Examples:" -ForegroundColor Gray
      Write-Host "  pwsh -File scripts/git_force_publish.ps1 -Remote 'git@github.com:ORG/REPO.git' -Branch $Branch" -ForegroundColor Gray
      Write-Host "  pwsh -File scripts/git_force_publish.ps1 -Remote 'https://github.com/ORG/REPO.git'" -ForegroundColor Gray
      Write-Host "Or set origin: git remote add origin <URL>" -ForegroundColor Gray
      exit 1
    }
  }
} else {
  if ($remoteTrim -match '^\s*mean\s*$') {
    throw "The provided -Remote value appears to be 'mean' (likely a typo). Please pass a valid Git remote URL, e.g., https://github.com/ORG/REPO.git or git@github.com:ORG/REPO.git."
  }
  if ($remoteTrim -eq 'origin') {
    if ($existingRemote) {
      Write-Info "Resolving -Remote 'origin' to existing URL: $existingRemote"
      $resolvedRemote = $existingRemote
    } else {
      throw "You passed -Remote 'origin' but no origin remote is configured. Please pass a full URL or run: git remote add origin <URL>"
    }
  } elseif (@('main','master','upstream') -contains $remoteTrim) {
    throw "The -Remote value '$Remote' is not a URL. Please provide the full Git remote URL, e.g., https://github.com/ORG/REPO.git or git@github.com:ORG/REPO.git."
  } else {
    if (-not ($remoteTrim -match $httpPattern -or $remoteTrim -match $sshPattern -or $remoteTrim -match $sshUrlPattern)) {
      throw "The -Remote value '$Remote' does not look like a valid Git remote URL. Examples: https://github.com/ORG/REPO.git or git@github.com:ORG/REPO.git"
    }
    $resolvedRemote = $remoteTrim
  }
}

# 7) Configure remote
if (Is-PlaceholderRemote $resolvedRemote) {
  Write-Warn "The resolved remote appears to be a placeholder: $resolvedRemote"
  $newRemote = Prompt-ForRemote "Enter a valid Git remote URL (e.g., https://github.com/your-org/your-repo.git). Press Enter to cancel"
  if ($newRemote) {
    $resolvedRemote = $newRemote
    Write-Info "Using provided remote URL: $resolvedRemote"
  } else {
    Write-Host "[USAGE] Please provide -Remote with a full Git URL or fix the origin: git remote set-url origin <URL>" -ForegroundColor Yellow
    exit 1
  }
}
Write-Step "Setting remote 'origin' to $resolvedRemote"
if (-not $DryRun) {
  # Fix common mistake: a remote accidentally named 'mean' (redundant check, safe)
  try {
    $remotes = (git remote).Trim().Split([Environment]::NewLine) | Where-Object { $_ -ne '' }
  } catch { $remotes = @() }
  if ($remotes -and ($remotes -contains 'mean') -and -not ($remotes -contains 'origin')) {
    Write-Warn "Detected remote named 'mean'. Renaming it to 'origin'."
    try { git remote rename mean origin | Out-Null } catch { Write-Warn "Failed to rename remote 'mean' to 'origin': $($_.Exception.Message)" }
  }

  $existingRemote = ''
  try { $existingRemote = (git remote get-url origin) } catch { $existingRemote = '' }
  if ($existingRemote) {
    if ($existingRemote -ne $resolvedRemote) { git remote set-url origin $resolvedRemote | Out-Null }
  } else {
    git remote add origin $resolvedRemote | Out-Null
  }
}

# 8) Push
Write-Step "Pushing to $resolvedRemote ($Branch)"
$pushArgs = @('push','-u','origin',$Branch)
if ($Force) { $pushArgs += '--force-with-lease' }
if ($SkipHooks) { $pushArgs += '--no-verify' }

function Convert-SshToHttps($sshUrl) {
  # Supports GitHub style ssh: git@github.com:ORG/REPO.git -> https://github.com/ORG/REPO.git
  if ($sshUrl -match '^git@github.com:([^/]+)/(.+?)\.git$') {
    $org = $Matches[1]
    $repo = $Matches[2]
    return "https://github.com/$org/$repo.git"
  }
  if ($sshUrl -match '^ssh://git@github.com/([^/]+)/(.+?)\.git$') {
    $org = $Matches[1]
    $repo = $Matches[2]
    return "https://github.com/$org/$repo.git"
  }
  return $null
}

if ($DryRun) {
  Write-Warn "Dry-run enabled: skipping push. Would run: git $($pushArgs -join ' ')"
} else {
  $gitOutput = & git @pushArgs 2>&1
  $exit = $LASTEXITCODE
  if ($exit -ne 0) {
    $outText = ($gitOutput | Out-String)

    # Handle non-fast-forward (remote is ahead) by offering pull --rebase then retry push
    $isNonFastForward = ($outText -match '(?i)non-fast-forward' -or $outText -match '(?i)tip of your current branch is behind' -or $outText -match '(?i)Updates were rejected because the tip of your current branch is behind')
    if ($isNonFastForward) {
      Write-Warn "Push rejected: remote is ahead (non-fast-forward)."
      $doRebase = $false
      if ($env:GIT_FORCE_PUBLISH_AUTO_REBASE) {
        $doRebase = ($env:GIT_FORCE_PUBLISH_AUTO_REBASE -match '^(?i:1|true|yes|y)$')
      }
      if (-not $doRebase) {
        $ans = Read-Host "Run 'git pull --rebase origin $Branch' and retry push now? [y/N]"
        $doRebase = ($ans -match '^(?i:y(?:es)?)$')
      }
      if ($doRebase) {
        Write-Step "Pulling latest from origin/$Branch with rebase"
        $pullOutput = & git pull --rebase origin $Branch 2>&1
        $pullExit = $LASTEXITCODE
        if ($pullExit -ne 0) {
          Write-Warn "git pull --rebase failed. Git output:"
          Write-Host ($pullOutput | Out-String) -ForegroundColor DarkGray
          throw "git pull --rebase failed with exit code $pullExit"
        }
        Write-Step "Retrying push to origin/$Branch"
        $gitOutput2 = & git @pushArgs 2>&1
        $exit2 = $LASTEXITCODE
        if ($exit2 -ne 0) {
          Write-Warn "Retry push after rebase failed. Git output:"
          Write-Host ($gitOutput2 | Out-String) -ForegroundColor DarkGray
          throw "git push failed with exit code $exit2"
        } else {
          Write-Ok "Pushed branch '$Branch' to origin after rebase"
        }
      } else {
        throw "git push failed with exit code $exit"
      }
    } elseif ( ($outText -match 'Permission denied (publickey)') -and ($resolvedRemote -match '^git@') ) {
        Write-Warn "SSH authentication failed: Permission denied (publickey)."
        if ($HttpsFallback) {
          $https = Convert-SshToHttps -sshUrl $resolvedRemote
          if ($https) {
            Write-Step "Switching remote 'origin' to HTTPS ($https) and retrying push once"
            try {
              git remote set-url origin $https | Out-Null
              $resolvedRemote = $https
              $gitOutput2 = & git @pushArgs 2>&1
              $exit2 = $LASTEXITCODE
              if ($exit2 -ne 0) {
                Write-Warn "Retry over HTTPS failed. Git output:"
                Write-Host ($gitOutput2 | Out-String) -ForegroundColor DarkGray
                throw "git push failed with exit code $exit2"
              } else {
                Write-Ok "Pushed branch '$Branch' to origin (HTTPS fallback)"
              }
            } catch {
              throw $_
            }
          } else {
            Write-Warn "Could not derive HTTPS URL from SSH remote; please provide -Remote with an HTTPS URL."
            throw "git push failed with exit code $exit"
          }
        } else {
          $autoFallback = $false
          if ($env:GIT_FORCE_PUBLISH_AUTO_HTTPS) {
            $autoFallback = ($env:GIT_FORCE_PUBLISH_AUTO_HTTPS -match '^(?i:1|true|yes|y)$')
          }
          if (-not $autoFallback) {
            $ans = Read-Host "SSH auth failed. Switch remote to HTTPS and retry push now? [y/N]"
            $autoFallback = ($ans -match '^(?i:y(?:es)?)$')
          }
          if ($autoFallback) {
            $https = Convert-SshToHttps -sshUrl $resolvedRemote
            if ($https) {
              Write-Step "Switching remote 'origin' to HTTPS ($https) and retrying push once"
              try {
                git remote set-url origin $https | Out-Null
                $resolvedRemote = $https
                $gitOutput2 = & git @pushArgs 2>&1
                $exit2 = $LASTEXITCODE
                if ($exit2 -ne 0) {
                  Write-Warn "Retry over HTTPS failed. Git output:"
                  Write-Host ($gitOutput2 | Out-String) -ForegroundColor DarkGray
                  throw "git push failed with exit code $exit2"
                } else {
                  Write-Ok "Pushed branch '$Branch' to origin (HTTPS fallback)"
                }
              } catch {
                throw $_
              }
            } else {
              Write-Warn "Could not derive HTTPS URL from SSH remote; please provide -Remote with an HTTPS URL."
              throw "git push failed with exit code $exit"
            }
          } else {
            Write-Host "[HINT] To auto-fallback to HTTPS, re-run with -HttpsFallback, or fix SSH by adding your public key to GitHub." -ForegroundColor Yellow
            Write-Host "       See: https://docs.github.com/en/authentication/connecting-to-github-with-ssh" -ForegroundColor Gray
            Write-Host "       Or switch remote to HTTPS: git remote set-url origin https://github.com/ORG/REPO.git" -ForegroundColor Gray
            throw "git push failed with exit code $exit"
          }
        }
      }
    else {
      # Other failure; show output for clarity then throw
      if ($outText -match 'Repository not found') {
        Write-Warn "Remote repository not found. The 'origin' URL may be incorrect or you may not have access."
        $newRemote = Prompt-ForRemote "Enter a valid Git remote URL to update 'origin' and retry push once [press Enter to cancel]"
        if ($newRemote) {
          Write-Step "Updating remote 'origin' to $newRemote and retrying push once"
          try {
            git remote set-url origin $newRemote | Out-Null
            $resolvedRemote = $newRemote
            $gitOutputRetry = & git @pushArgs 2>&1
            $exitRetry = $LASTEXITCODE
            if ($exitRetry -ne 0) {
              Write-Warn "Retry after updating remote failed. Git output:"
              Write-Host ($gitOutputRetry | Out-String) -ForegroundColor DarkGray
              throw "git push failed with exit code $exitRetry"
            } else {
              Write-Ok "Pushed branch '$Branch' to origin"
            }
          } catch {
            throw $_
          }
        } else {
          Write-Warn "No valid remote provided."
          Write-Warn "git push failed. Git output:"
          Write-Host $outText -ForegroundColor DarkGray
          throw "git push failed with exit code $exit"
        }
      } else {
        Write-Warn "git push failed. Git output:"
        Write-Host $outText -ForegroundColor DarkGray
        throw "git push failed with exit code $exit"
      }
    }
  } else {
    Write-Ok "Pushed branch '$Branch' to origin"
  }
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
