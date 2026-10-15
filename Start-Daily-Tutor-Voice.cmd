@echo off
chcp 65001 >nul
cd /d "%~dp0"
set "PYTHONIOENCODING=utf-8"
rem Fixed-WAV pause follow-up: two consecutive one-ASR/tool/audio scenes; see docs/evidence/codex-r2-p2-pause-2026-10-16.md.
set "NEKO_PAUSE_HOLD=1"
set "NEKO_PAUSE_HOLD_KEEP_MS=100"
set "NEKO_PAUSE_HOLD_MS=1500"
"%~dp0benchmarks\raw\neko-product-host\.venv\Scripts\python.exe" "%~dp0scripts\neko_tutor_start.py" --store neko-daily-companion --budget-round bargein-autocheck-20261012 --egress-budget 2000 --api-budget 80 --voice --voice-host www.lanlan.app --voice-connects unlimited --study-ui --learning-surface --code-root keep %*
if errorlevel 1 pause
