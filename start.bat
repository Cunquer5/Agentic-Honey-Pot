@echo off
REM Quick start script for Windows
REM Automates the setup and launch process

echo ========================================
echo Agentic Honey-Pot - Quick Start
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH
    echo Please install Python 3.10+ from https://www.python.org/
    pause
    exit /b 1
)

echo [OK] Python found
echo.

REM Check if Ollama is installed
ollama --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Ollama is not installed
    echo Please install from https://ollama.com/download/windows
    echo Or run: winget install Ollama.Ollama
    pause
    exit /b 1
)

echo [OK] Ollama found
echo.

REM Check if model is downloaded
echo Checking for LLM model...
ollama list | findstr "llama3.2:1b-instruct-q4_K_M" >nul 2>&1
if errorlevel 1 (
    echo [INFO] Model not found. Downloading (this may take a few minutes)...
    ollama pull llama3.2:1b-instruct-q4_K_M
    if errorlevel 1 (
        echo [ERROR] Failed to download model
        echo Try smaller model: ollama pull llama3.2:3b-instruct-q4_K_M
        pause
        exit /b 1
    )
)

echo [OK] Model ready
echo.

REM Install Python dependencies
echo Installing Python dependencies...
pip install -r requirements.txt >nul 2>&1
if errorlevel 1 (
    echo [WARNING] Some dependencies may have failed to install
    echo Continuing anyway...
)

echo [OK] Dependencies installed
echo.

REM Check if .env exists
if not exist .env (
    echo [INFO] Creating .env file from template...
    copy .env.example .env >nul
)

echo ========================================
echo Starting Services
echo ========================================
echo.

REM Start Ollama server in background
echo [1/2] Starting Ollama server...
start /B ollama serve
timeout /t 3 /nobreak >nul

echo [2/2] Starting API server...
echo.
echo ========================================
echo API Server Running
echo ========================================
echo.
echo URL: http://localhost:8000
echo Docs: http://localhost:8000/docs
echo Health: http://localhost:8000/health
echo.
echo Press Ctrl+C to stop
echo ========================================
echo.

REM Start the API server
python app.py

REM Cleanup on exit
echo.
echo Shutting down...
taskkill /F /IM ollama.exe >nul 2>&1
