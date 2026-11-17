@echo off
chcp 65001 >nul
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Patch.ps1" -Action Check
if errorlevel 1 echo 操作未成功，请查看上面的错误信息。
pause
