@echo off
title SDET Job Suite — Dashboard
cd /d "%~dp0"
echo ===================================================
echo   Starting SDET Job Suite Dashboard
echo   URL: http://localhost:5000
echo ===================================================

if exist "%LOCALAPPDATA%\Programs\Python\Python313\python.exe" (
    "%LOCALAPPDATA%\Programs\Python\Python313\python.exe" dashboard\app.py
) else (
    python dashboard\app.py
)

pause

