@echo off
chcp 65001 >nul
title Hermes Copilot Server
cd /d "%~dp0"
echo ==============================================================
echo [INIT] Запуск Hermes Copilot Server на http://127.0.0.1:8080...
echo ==============================================================
python scripts\copilot_server.py --port 8080 --pregenerate 0
pause
