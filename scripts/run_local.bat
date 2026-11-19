
@echo off
title SkillMimic Robotics Studio

cd /d "%~dp0\.."

echo ======================================
echo       SKILLMIMIC ROBOTICS STUDIO
echo ======================================

if not exist "venv\Scripts\python.exe" (
    echo Virtual environment not found.
    echo Run scripts\setup_environment.bat first.
    pause
    exit /b 1
)

call venv\Scripts\activate.bat

echo Starting SkillMimic...
python -m streamlit run app\main.py

pause
