@echo off
title SDET Job Suite — Stop Background Service
echo Stopping SDET Job Suite background processes...
taskkill /F /IM python.exe /T 2>nul
echo Done! All background services stopped.
pause
