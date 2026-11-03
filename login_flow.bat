@echo off
title Login Google Flow
echo ========================================================
echo   Membuka Google Chrome dengan Profil Google Flow
echo   Profil: C:\Users\HP\.google-flow-creator\browser-profile
echo ========================================================
echo.
echo Silakan login akun Google Anda di jendela Chrome yang terbuka.
echo Setelah selesai login dan melihat dashboard flow.google.com,
echo Anda bisa menutup jendela browser tersebut.
echo.

start "" "chrome.exe" --user-data-dir="C:\Users\HP\.google-flow-creator\browser-profile" "https://flow.google.com/"
pause
