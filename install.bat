@echo off
REM OpenCellComms Installation Script for Windows
REM This script sets up the complete development environment

REM Always run from the directory where this script lives
cd /d "%~dp0"

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

REM Check npm (must use CALL with .cmd files or the parent batch exits silently)
call npm.cmd --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [X] npm not found. Please install Node.js/npm 7 or higher.
    echo     Download from: https://nodejs.org/
    pause
    exit /b 1
)
for /f "tokens=1" %%i in ('call npm.cmd --version 2^>^&1') do set NPM_VERSION=%%i
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

REM Install Flask server dependencies (anthropic powers the in-GUI coding agent)
pip install flask flask-cors anthropic >nul 2>&1
echo [OK] Flask server dependencies installed

cd ..

echo.
echo Installing adapter dependencies...

for /d %%D in (opencellcomms_adapters\*) do (
    if exist "%%D\requirements.txt" (
        echo   %%~nxD adapter...
        pip install -r "%%D\requirements.txt" >nul 2>&1
        if errorlevel 1 (
            echo [!] %%~nxD adapter: some dependencies failed ^(adapter will be skipped at runtime^)
        ) else (
            echo [OK] %%~nxD adapter dependencies installed
        )
    )
)

echo.
echo Installing GUI dependencies...

REM Install GUI dependencies
cd opencellcomms_gui
call npm.cmd install >nul 2>&1
echo [OK] GUI dependencies installed

cd ..

echo.
echo Installing developer tooling (tests + pre-commit hook)...
echo [!] Optional - if this step fails you can still run OpenCellComms.

REM Dev extras (pytest, linters, pre-commit) live in the engine's 'dev' optional
REM dependencies. Failures here are non-fatal: running the app must never depend
REM on the test stack.
cd opencellcomms_engine
pip install -e ".[dev]" >nul 2>&1
if errorlevel 1 (
    echo [!] Developer dependencies failed - app still runs; tests won't until fixed
) else (
    echo [OK] Developer dependencies installed ^(pytest, linters, pre-commit^)
)
cd ..

REM Activate the git pre-commit hook (runs the fast engine tests at commit time).
where pre-commit >nul 2>&1
if errorlevel 1 (
    echo [!] pre-commit unavailable - skipping hook ^(run 'pre-commit install' manually^)
) else (
    pre-commit install >nul 2>&1
    if errorlevel 1 (
        echo [!] Could not install pre-commit hook - run 'pre-commit install' manually
    ) else (
        echo [OK] pre-commit hook installed ^(fast engine tests run on commit^)
    )
)

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

