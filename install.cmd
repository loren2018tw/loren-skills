@echo off
setlocal EnableExtensions
rem Run install.ps1 with PowerShell 7 (pwsh). install.ps1 requires pwsh 7.2+.
rem This wrapper finds pwsh and checks its version; when pwsh is missing it
rem prints install guidance and exits without changing anything.
rem -ExecutionPolicy Bypass avoids the default Restricted policy blocking
rem script execution.

set "PWSH="
where pwsh >nul 2>nul && set "PWSH=pwsh"
if not defined PWSH if exist "%ProgramFiles%\PowerShell\7\pwsh.exe" set "PWSH=%ProgramFiles%\PowerShell\7\pwsh.exe"
if not defined PWSH if exist "%LOCALAPPDATA%\Microsoft\WindowsApps\pwsh.exe" set "PWSH=%LOCALAPPDATA%\Microsoft\WindowsApps\pwsh.exe"

if not defined PWSH (
  echo [ERROR] PowerShell 7 -- pwsh -- was not found. install.ps1 requires pwsh 7.2 or later.
  echo Install it with one command:  winget install -e --id Microsoft.PowerShell
  echo Other options: Microsoft Store, or https://aka.ms/powershell
  echo See the README.md Windows section. No changes were made.
  exit /b 1
)

"%PWSH%" -NoProfile -ExecutionPolicy Bypass -Command "if ($PSVersionTable.PSVersion -lt [version]'7.2') { exit 1 }"
if errorlevel 1 (
  echo [ERROR] pwsh was found but is older than 7.2, or could not be run.
  echo Update it with:  winget upgrade -e --id Microsoft.PowerShell
  echo See the README.md Windows section. No changes were made.
  exit /b 1
)

"%PWSH%" -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1" %*
if errorlevel 1 exit /b 1
exit /b 0
