@echo off
REM OpenCellComms Installation Script for Windows
REM This script sets up the complete development environment

echo ================================================================
echo           OpenCellComms Installation Script
echo ================================================================
echo.

REM Check Python
python --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [X] Python not found. Please install Python 3.8 or higher.
    echo     Download from: https://www.python.org/downloads/
    pause
    exit /b 1
)
for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo [OK] Python found: %PYTHON_VERSION%

REM Check Node.js
node --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [X] Node.js not found. Please install Node.js 18 or higher.
    echo     Download from: https://nodejs.org/
    pause
    exit /b 1
)
for /f "tokens=1" %%i in ('node --version 2^>^&1') do set NODE_VERSION=%%i
echo [OK] Node.js found: %NODE_VERSION%

REM Check npm
npm --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [X] npm not found. Please install npm 7 or higher.
    pause
    exit /b 1
)
for /f "tokens=1" %%i in ('npm --version 2^>^&1') do set NPM_VERSION=%%i
echo [OK] npm found: %NPM_VERSION%

echo.
echo Creating Python virtual environment...

REM Create virtual environment if it doesn't exist
if not exist ".venv" (
    python -m venv .venv
    echo [OK] Virtual environment created: .venv\
) else (
    echo [!] Virtual environment already exists: .venv\
)

REM Activate virtual environment
call .venv\Scripts\activate
echo [OK] Virtual environment activated

echo.
echo Installing Python engine...

REM Install the engine package
cd opencellcomms_engine
pip install --upgrade pip >nul 2>&1
pip install -e . >nul 2>&1
echo [OK] OpenCellComms engine installed

REM Install Flask server dependencies
pip install flask flask-cors >nul 2>&1
echo [OK] Flask server dependencies installed

cd ..

echo.
echo Installing GUI dependencies...

REM Install GUI dependencies
cd opencellcomms_gui
call npm install >nul 2>&1
echo [OK] GUI dependencies installed

cd ..

echo.
echo ================================================================
echo              Installation Complete!
echo ================================================================
echo.
echo To get started:
echo.
echo   1. Activate the virtual environment:
echo      .venv\Scripts\activate
echo.
echo   2. Run OpenCellComms:
echo      run.bat
echo.
echo   3. Open http://localhost:3000 in your browser
echo.
echo For more information, see docs\INSTALL.md and docs\USAGE.md
echo.
pause

