@echo off
REM OpenCellComms Launch Script for Windows
REM Starts both the backend server and frontend development server

echo ================================================================
echo              OpenCellComms Launcher
echo ================================================================
echo.

REM Get the directory where this script is located
set SCRIPT_DIR=%~dp0
cd /d "%SCRIPT_DIR%"

REM Activate virtual environment
if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate
) else if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate
) else (
    echo [!] No virtual environment found. Please run install.bat first.
    pause
    exit /b 1
)

echo [OK] Virtual environment activated

echo.
echo [!] Starting servers in separate windows...
echo [!] Close the server windows to stop the application.
echo.

REM Start Flask backend server in a new window
echo [...] Starting backend server...
start "OpenCellComms Backend" cmd /k "cd /d %SCRIPT_DIR%opencellcomms_gui\server && python api.py"

REM Wait for backend to start
timeout /t 3 /nobreak >nul

echo [OK] Backend server started

REM Start React frontend in a new window
echo [...] Starting frontend server...
start "OpenCellComms Frontend" cmd /k "cd /d %SCRIPT_DIR%opencellcomms_gui && npm run dev"

REM Wait for frontend to start
timeout /t 3 /nobreak >nul

echo [OK] Frontend server started

echo.
echo ================================================================
echo              OpenCellComms is Running!
echo ================================================================
echo.
echo   Frontend:  http://localhost:3000
echo   Backend:   http://localhost:5001
echo.
echo   Close the server windows to stop the application.
echo   Or close this window (servers will keep running).
echo.

REM Open browser
echo Opening browser...
start http://localhost:3000

echo.
pause

