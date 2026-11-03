@echo off
title MicroDrama AI Launcher
echo ========================================================
echo   Launching MicroDrama AI System
echo   1. Backend Server (FastAPI + Omni Flash Engine)
echo   2. Frontend UI (Next.js)
echo ========================================================

start "" "D:\microdrama-app\run_server.bat"
start "" "D:\microdrama-app\run_client.bat"

echo.
echo Kedua service sedang dibuka di window terpisah.
echo Akses Web UI di: http://localhost:3000
echo.
timeout /t 5
