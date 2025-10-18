#requires -Version 5.1
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

Write-Host '== Preflight Checks ==' -ForegroundColor Cyan

function Test-Cmd($name) {
  try { Get-Command $name -ErrorAction Stop | Out-Null; return $true } catch { return $false }
}

# Python
if (Test-Cmd 'python') {
  $pyv = (python --version) 2>$null
  Write-Host ("Python: {0}" -f $pyv) -ForegroundColor DarkGray
} else {
  Write-Warning 'Python not found on PATH.'
}

# Docker
if (Test-Cmd 'docker') {
  try {
    $info = docker info 2>$null
    Write-Host 'Docker: available' -ForegroundColor DarkGray
  } catch { Write-Warning 'Docker seems installed but not running (open Docker Desktop).'}
} else {
  Write-Warning 'Docker not found on PATH.'
}

# Node/npm
if (Test-Cmd 'npm') {
  $nv = (npm -v) 2>$null
  Write-Host ("npm: {0}" -f $nv) -ForegroundColor DarkGray
} else {
  Write-Host 'npm: not found (only required for frontend dev server).' -ForegroundColor DarkGray
}

# Redis/PG quick TCP probes (defaults)
function Test-Tcp($RemoteHost, $Port, $Label) {
  try {
    $client = New-Object System.Net.Sockets.TcpClient
    $iar = $client.BeginConnect($RemoteHost, $Port, $null, $null)
    $ok = $iar.AsyncWaitHandle.WaitOne(1000, $false)
    if ($ok -and $client.Connected) { Write-Host ("{0}: {1}:{2} reachable" -f $Label,$RemoteHost,$Port) -ForegroundColor DarkGray }
    else { Write-Host ("{0}: {1}:{2} not reachable (may be fine if not started yet)" -f $Label,$RemoteHost,$Port) -ForegroundColor DarkYellow }
    $client.Close()
  } catch {
    Write-Host ("{0}: error probing {1}:{2} - {3}" -f $Label,$RemoteHost,$Port,$_.Exception.Message) -ForegroundColor DarkYellow
  }
}

Test-Tcp '127.0.0.1' 5432 'PostgreSQL'
Test-Tcp '127.0.0.1' 6379 'Redis'

Write-Host 'Preflight completed.' -ForegroundColor Green