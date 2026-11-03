@echo off
title MicroDrama AI - Next.js Web UI (Port 3000)
cd /d "D:\microdrama-app\client"

if not exist node_modules (
    echo Installing Next.js dependencies...
    call npm install
)

echo ========================================================
echo   Starting MicroDrama Web UI at http://localhost:3000
echo ========================================================

npm run dev
pause
