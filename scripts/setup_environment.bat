
@echo off
title SkillMimic Environment Setup

cd /d "%~dp0\.."

echo ======================================
echo       SKILLMIMIC SETUP
echo ======================================

where py >nul 2>nul

if errorlevel 1 (
    echo Python Launcher was not found.
    echo Please install Python 3.11 first.
    pause
    exit /b 1
)

if not exist "venv\Scripts\python.exe" (
    echo Creating Python virtual environment...
    py -3.11 -m venv venv

    if errorlevel 1 (
        echo Virtual environment creation failed.
        pause
        exit /b 1
    )
)

echo Activating environment...
call venv\Scripts\activate.bat

echo Installing dependencies...
python -m pip install -r requirements.txt

if errorlevel 1 (
    echo Dependency installation failed.
    pause
    exit /b 1
)

echo.
echo SkillMimic environment setup completed.
pause
