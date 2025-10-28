@echo off
setlocal
REM Simple double-click launcher for Windows

set SCRIPT_DIR=%~dp0
set PS1=%SCRIPT_DIR%start_here.ps1

REM Prefer PowerShell 7 (pwsh), fallback to Windows PowerShell
where pwsh >nul 2>nul
if %ERRORLEVEL%==0 (
  pwsh -NoProfile -ExecutionPolicy Bypass -File "%PS1%"
  exit /b %ERRORLEVEL%
) else (
  powershell -NoProfile -ExecutionPolicy Bypass -File "%PS1%"
  exit /b %ERRORLEVEL%
)