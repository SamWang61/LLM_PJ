@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Start-SRJ.ps1" -Role REN
if errorlevel 1 pause
