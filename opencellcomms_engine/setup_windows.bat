@echo off
REM MicroC Windows Setup Script
REM This replaces the Unix Makefile for Windows users

echo MicroC Windows Setup and Development Commands
echo.

if "%1"=="" goto help
if "%1"=="help" goto help
if "%1"=="install" goto install
if "%1"=="install-dev" goto install-dev
if "%1"=="install-minimal" goto install-minimal
if "%1"=="test" goto test
if "%1"=="test-fast" goto test-fast
if "%1"=="clean" goto clean
if "%1"=="run-example" goto run-example
goto help

:help
echo Available commands:
echo.
echo Setup and Installation:
echo   setup_windows.bat install          Install MicroC in production mode
echo   setup_windows.bat install-dev      Install MicroC in development mode
echo   setup_windows.bat install-minimal  Install only core dependencies
echo.
echo Testing:
echo   setup_windows.bat test             Run all tests
echo   setup_windows.bat test-fast        Run fast tests only
echo.
echo Utilities:
echo   setup_windows.bat clean            Clean build artifacts
echo   setup_windows.bat run-example      Run example simulation
echo.
goto end

:install
echo Installing MicroC in production mode...
python -m pip install .
goto end

:install-dev
echo Installing MicroC in development mode...
python -m pip install -e ".[dev,docs,jupyter,performance,visualization]"
goto end

:install-minimal
echo Installing MicroC with minimal dependencies...
python -m pip install -e .
goto end

:test
echo Running all tests...
python -m pytest tests/ -v
goto end

:test-fast
echo Running fast tests only...
python -m pytest tests/ -v -m "not slow"
goto end

:clean
echo Cleaning build artifacts...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist *.egg-info rmdir /s /q *.egg-info
for /d /r . %%d in (__pycache__) do @if exist "%%d" rmdir /s /q "%%d"
del /s /q *.pyc 2>nul
goto end

:run-example
echo Running example simulation...
python run_sim.py tests/jayatilake_experiment/jayatilake_experiment_config.yaml --steps 10
goto end

:end
