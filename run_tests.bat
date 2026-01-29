@echo off
REM Test runner script for Windows

echo ========================================
echo Running Agentic Honey-Pot Tests
echo ========================================
echo.

echo Choose environment:
echo 1. Local (localhost:8000)
echo 2. Cloud (Hugging Face)
echo.
set /p env_choice="Enter choice (1-2): "

if "%env_choice%"=="2" (
    set BASE_URL=https://Conquerer55555-Agentic-honey-pot.hf.space
) else (
    set BASE_URL=http://localhost:8000
    REM Check if local server is running
    curl -s http://localhost:8000/health >nul 2>&1
    if errorlevel 1 (
        echo [ERROR] Local API server is not running
        echo Please start it with start.bat or python app.py
        pause
        exit /b 1
    )
)

echo [OK] Using endpoint: %BASE_URL%
echo.

echo Choose test type:
echo 1. Quick Test (health check only)
echo 2. Full Test Suite
echo 3. Mock Scammer Simulation
echo 4. Performance Benchmark
echo 5. All Tests
echo.

set /p choice="Enter choice (1-5): "

if "%choice%"=="1" (
    echo.
    echo Running health check...
    curl %BASE_URL%/health
    echo.
) else if "%choice%"=="2" (
    echo.
    echo Running full test suite...
    python test_api.py
) else if "%choice%"=="3" (
    echo.
    echo Running mock scammer simulation...
    python mock_scammer.py
) else if "%choice%"=="4" (
    echo.
    echo Running performance benchmarks...
    python benchmark.py
) else if "%choice%"=="5" (
    echo.
    echo Running all tests...
    echo.
    echo === Health Check ===
    curl %BASE_URL%/health
    echo.
    echo.
    echo === Full Test Suite ===
    python test_api.py
    echo.
    echo === Mock Simulation ===
    python mock_scammer.py
    echo.
    echo === Benchmarks ===
    python benchmark.py
) else (
    echo Invalid choice
)

echo.
pause
