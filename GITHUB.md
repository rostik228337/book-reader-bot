# Как выложить на GitHub и включить Pages

## ШАГ 1. Установить Git (если нет)
https://git-scm.com/download/win — все параметры по умолчанию. Проверка:
```powershell
git --version
```

## ШАГ 2. Создать репозиторий на GitHub
1. https://github.com → <kbd>+</kbd> → <kbd>New repository</kbd>
2. Name: `book-reader-bot` (или любое)
3. **Public** — обязательно, иначе GitHub Pages не включится на бесплатном тарифе
4. НЕ ставь галочки «Add README», «.gitignore», «license» — у нас всё уже есть
5. <kbd>Create repository</kbd> → скопируй URL

## ШАГ 3. Пушнуть проект

```powershell
cd "C:\Users\User\Documents\Claude\Projects\ПРОЕКТ КНИГА"
git init
git add .
git status
```

**Проверь `git status` — должно быть:**
- `README.md`, `ТЗ.md`, `GITHUB.md`, `УСТАНОВКА.md`, `.gitignore`
- `docs/index.html`, `docs/app.js`, `docs/style.css`, `docs/chapters.json`

**НЕ должно быть** `backend/`, `webapp/`, `bot/`, `setup.bat`, `run.bat`, `*.env` — всё это в `.gitignore`.

Если всё ок:
```powershell
git commit -m "initial: static mini app on github pages"
git branch -M main
git remote add origin https://github.com/ТВОЙ_НИК/book-reader-bot.git
git push -u origin main
```

Первый пуш попросит логин. Пароль НЕ сработает — нужен **Personal Access Token**:
1. https://github.com/settings/tokens → Generate new token (classic)
2. Scope: `repo`
3. Скопируй, вставь вместо пароля

## ШАГ 4. Включить GitHub Pages

1. Репо на github.com → **Settings** → **Pages**
2. **Source:** Deploy from a branch
3. **Branch:** `main` / **Folder:** `/docs`
4. Save

Через 30–60 сек появится URL:
```
https://<твой-ник>.github.io/book-reader-bot/
```

Открой — должно загрузиться (вне Telegram покажет либо UI книги, либо заглушку).

## ШАГ 5. Вставить URL в BotFather

1. Telegram → [@BotFather](https://t.me/BotFather)
2. `/mybots` → твой бот
3. **Bot Settings** → **Menu Button** → **Configure menu button**
4. URL: тот что с шага 4
5. Название: `📖 Открыть книгу`

## Обновление

Изменил что-то:
```powershell
cd "C:\Users\User\Documents\Claude\Projects\ПРОЕКТ КНИГА"
git add .
git commit -m "что изменил"
git push
```

Pages пересоберёт автоматически через ~30 сек.
