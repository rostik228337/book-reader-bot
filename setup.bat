@echo off
chcp 65001 >nul
echo ============================================
echo   Установка зависимостей бота
echo ============================================
echo.

cd /d "%~dp0bot"

if not exist venv (
    echo Создаю виртуальное окружение...
    python -m venv venv
    if errorlevel 1 (
        echo ОШИБКА: не удалось создать venv. Проверь что Python установлен и в PATH.
        pause
        exit /b 1
    )
)

echo Активирую venv и ставлю пакеты...
call venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt

echo.
echo ============================================
echo   Готово! Теперь:
echo   1. Проверь что в bot\.env вписан BOT_TOKEN
echo   2. Запусти run.bat
echo ============================================
pause
