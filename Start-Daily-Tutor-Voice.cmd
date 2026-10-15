@echo off
chcp 65001 >nul
cd /d "%~dp0"
set "PYTHONIOENCODING=utf-8"
rem Keep mid-sentence pauses from splitting one question into two turns (docs/evidence/claude-m3-split-asr-analysis-2026-10-15.md).
set "NEKO_PAUSE_HOLD=1"
"%~dp0benchmarks\raw\neko-product-host\.venv\Scripts\python.exe" "%~dp0scripts\neko_tutor_start.py" --store neko-daily-companion --budget-round bargein-autocheck-20261012 --egress-budget 2000 --api-budget 80 --voice --voice-host www.lanlan.app --voice-connects unlimited --study-ui --learning-surface --code-root keep %*
if errorlevel 1 pause
