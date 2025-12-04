@echo off
REM QuickChat Windows Run Script
REM This script activates the virtual environment and runs the app

REM Check if venv exists
if not exist venv (
    echo ERROR: Virtual environment not found!
    echo Please run setup.bat first
    pause
    exit /b 1
)

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Run the application
python main.py

REM Deactivate venv on exit
deactivate
