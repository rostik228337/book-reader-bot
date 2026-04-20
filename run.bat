@echo off
chcp 65001 >nul
cd /d "%~dp0backend"

if not exist venv (
    echo ОШИБКА: нет venv. Сначала запусти setup.bat
    pause
    exit /b 1
)

call venv\Scripts\activate.bat
python run.py
pause
