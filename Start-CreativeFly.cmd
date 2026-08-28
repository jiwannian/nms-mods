@echo off
setlocal
set "SCRIPT_DIR=%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%Start-CreativeFly.ps1"
if errorlevel 1 (
    echo 启动失败，请确认 D:\tool\AutoHotkey\AutoHotkey64.exe 存在。
    pause
)
endlocal
