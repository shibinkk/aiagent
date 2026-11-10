@echo off
title SDET Job Suite — Agent
cd /d "%~dp0"
echo Starting AI Job Search Agent...

if exist "%LOCALAPPDATA%\Programs\Python\Python313\python.exe" (
    "%LOCALAPPDATA%\Programs\Python\Python313\python.exe" main.py
) else (
    python main.py
)
pause
