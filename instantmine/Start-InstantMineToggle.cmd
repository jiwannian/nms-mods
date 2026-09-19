@echo off
setlocal
cd /d "%~dp0"
set "PY=C:\Program Files\Python310\python.exe"
if exist "%PY%" (
    "%PY%" instantmine_toggle.py
) else (
    python instantmine_toggle.py
)
endlocal
