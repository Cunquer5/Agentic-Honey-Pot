@echo off
REM Test runner script for Windows

echo ========================================
echo Running Agentic Honey-Pot Tests
echo ========================================
echo.

REM Check if server is running
curl -s http://localhost:8000/health >nul 2>&1
if errorlevel 1 (
    echo [ERROR] API server is not running
    echo Please start the server first with: start.bat
    echo Or manually: python app.py
    pause
    exit /b 1
)

echo [OK] API server is running
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
    curl http://localhost:8000/health
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
    curl http://localhost:8000/health
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
