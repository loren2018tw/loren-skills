@echo off
rem Run install.ps1 with ExecutionPolicy Bypass.
rem The Windows default policy (Restricted) blocks .ps1 files;
rem this wrapper avoids asking the user to change system settings.
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1" %*
exit /b %ERRORLEVEL%
