@echo off
echo ============================================
echo   AI Job Search Agent — Setup Script
echo ============================================
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found! Install from https://python.org
    pause
    exit /b
)

echo [1/5] Creating virtual environment...
python -m venv venv
call venv\Scripts\activate.bat

echo [2/5] Installing dependencies...
pip install --upgrade pip -q
pip install -r requirements.txt

echo [3/5] Setting up .env file...
if not exist .env (
    copy .env.example .env
    echo      [!] .env created. Please edit it with your credentials.
) else (
    echo      .env already exists, skipping.
)

echo [4/5] Creating folders...
mkdir resume 2>nul
mkdir logs 2>nul
mkdir data 2>nul

echo [5/5] Done!
echo.
echo ============================================
echo   NEXT STEPS:
echo   1. Add your resume PDF as: resume\resume.pdf
echo   2. Edit .env with Telegram + Email creds
echo   3. Edit config.yaml to set your target roles
echo   4. Install Ollama: https://ollama.com
echo   5. Run: ollama pull llama3
echo   6. Run: python main.py
echo   7. Open: http://localhost:5000
echo ============================================
pause
