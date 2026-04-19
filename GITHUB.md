# Как выложить проект на GitHub

## ШАГ 1. Установить Git
Скачать: https://git-scm.com/download/win
При установке — все параметры по умолчанию. После установки в PowerShell проверь:
```powershell
git --version
```

## ШАГ 2. Зарегистрироваться на GitHub
Если ещё нет аккаунта: https://github.com/signup

## ШАГ 3. Создать репозиторий на GitHub
1. Зайди на https://github.com → нажми <kbd>+</kbd> → <kbd>New repository</kbd>
2. Repository name: `book-reader-bot` (или любое другое)
3. **Private** — если хочешь чтобы никто кроме тебя не видел (рекомендую)
4. **НЕ ставь** галочки «Add README», «Add .gitignore», «license» — у нас всё это уже есть
5. Нажми <kbd>Create repository</kbd>
6. На следующей странице скопируй URL из блока «…or push an existing repository from the command line». Он вида:
   ```
   https://github.com/ТВОЙ_НИК/book-reader-bot.git
   ```

## ШАГ 4. Инициализировать git локально и запушить
Открой PowerShell в папке проекта:
```powershell
cd "C:\Users\User\Documents\Claude\Projects\ПРОЕКТ КНИГА"
git init
git add .
git status
```

**⚠️ ВАЖНО — проверь вывод `git status`:**
- Должны добавиться: `README.md`, `.gitignore`, `УСТАНОВКА.md`, `ТЗ.md`, `ПРОМТ_ДЛЯ_КОДА.md`, `GITHUB.md`, `setup.bat`, `run.bat`, `bot/*.py`, `bot/requirements.txt`, `bot/.env.example`, `data/chapters.json`
- **НЕ должно быть** `bot/.env` — если он в списке, значит `.gitignore` не сработал, СТОП и пиши мне

Если всё ок:
```powershell
git commit -m "initial: book reader telegram bot"
git branch -M main
git remote add origin https://github.com/ТВОЙ_НИК/book-reader-bot.git
git push -u origin main
```

При первом пуше GitHub попросит логин. Используй **Personal Access Token** (не пароль):
1. https://github.com/settings/tokens → Generate new token (classic)
2. Scope: `repo` (галочку)
3. Скопируй токен → вставь вместо пароля

## ШАГ 5. Проверить на GitHub
Зайди на страницу репозитория — убедись, что `bot/.env` **отсутствует** в списке файлов. Если вдруг видишь его там — токен бота скомпрометирован, нужно отзывать через @BotFather.

## Как потом обновлять код
После любых изменений:
```powershell
cd "C:\Users\User\Documents\Claude\Projects\ПРОЕКТ КНИГА"
git add .
git commit -m "что изменил"
git push
```

## Клонирование на другой компьютер
```powershell
git clone https://github.com/ТВОЙ_НИК/book-reader-bot.git
cd book-reader-bot
copy bot\.env.example bot\.env
notepad bot\.env      # вписать BOT_TOKEN и ADMIN_USER_ID
setup.bat             # поставить зависимости
run.bat               # запустить
```
