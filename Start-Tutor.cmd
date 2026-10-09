@echo off
chcp 65001 >nul
cd /d "%~dp0"
set "PYTHONIOENCODING=utf-8"
"%~dp0benchmarks\raw\neko-product-host\.venv\Scripts\python.exe" "%~dp0scripts\neko_tutor_start.py" %*
if errorlevel 1 pause
