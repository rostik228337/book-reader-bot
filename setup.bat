@echo off
chcp 65001 >nul
echo ============================================
echo   Установка зависимостей (backend)
echo ============================================
echo.

cd /d "%~dp0backend"

if not exist venv (
    echo Создаю виртуальное окружение...
    python -m venv venv
    if errorlevel 1 (
        echo ОШИБКА: не удалось создать venv. Проверь что Python 3.11+ установлен.
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
echo   Готово! Дальше:
echo   1. Скопируй backend\.env.example -^> backend\.env
echo   2. Впиши BOT_TOKEN, ADMIN_USER_ID
echo   3. Запусти ngrok http 8000, скопируй URL
echo   4. Впиши URL в backend\.env -^> WEBAPP_URL
echo   5. Запусти run.bat
echo ============================================
pause
