@echo off
title MicroDrama AI - Backend Server (Port 8000)
cd /d "D:\microdrama-app\server"

echo ========================================================
echo   Starting MicroDrama AI Server (Google Omni Flash 1.1)
echo   LLM Router: 9Router (http://localhost:20128/v1)
echo   Video Engine: Google Omni Flash 1.1 (9:16 Portrait)
echo ========================================================

"C:\Users\HP\AppData\Local\Programs\Python\Python312\python.exe" -m uvicorn api:app --host 0.0.0.0 --port 8000 --reload
pause
