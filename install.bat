@echo off
chcp 65001 > nul
setlocal EnableDelayedExpansion

echo ========================================
echo Electronic Lab Notebook - Launcher
echo ========================================

REM Check Python
python --version > nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found! Install Python from python.org
    pause
    exit /b 1
)
echo [OK] Python found.

REM Create Venv if not exists
if not exist venv (
    echo Creating virtual environment...
    python -m venv venv
) else (
    echo [OK] Virtual environment found.
)

REM Activate Venv
call venv\Scripts\activate.bat

REM Check and Install Dependencies
pip show flask > nul 2>&1
if errorlevel 1 (
    echo Installing Flask...
    pip install flask
) else (
    echo [OK] Dependencies already installed. Skipping installation.
)

REM Create directories
if not exist uploads mkdir uploads
if not exist data mkdir data

echo ========================================
echo Starting Server...
echo Open browser: http://127.0.0.1:5000
echo Press Ctrl+C to stop
echo ========================================

start "" http://127.0.0.1:5000
python app.py

pause