# ПРОЕКТ КНИГА — Telegram Mini App

Mini App для усвоения книги «Почему бедные страны беднеют, а богатые страны богатеют» (Эрик Райнерт) через открытые вопросы после каждой главы.

**Полностью статический** — без бэкенда, без хостинга, без ngrok. Живёт на GitHub Pages, URL вставляется в BotFather.

## Как работает

1. Открываешь бота → жмёшь кнопку «Открыть книгу» → запускается Mini App
2. Выбираешь главу
3. Бот задаёт 3–7 открытых вопросов
4. Отвечаешь своими словами — оценка по ключевым словам (стемминг русского на JS)
5. Все вопросы на 2 балла → глава пройдена, открывается следующая
6. Иначе → «Перечитай главу и попробуй снова»

Прогресс хранится в **Telegram CloudStorage** — синхронится между твоими устройствами автоматически.

## Стек

- HTML + CSS + ванильный JavaScript
- Telegram WebApp SDK (`telegram-web-app.js`)
- GitHub Pages — хостинг
- `chapters.json` — контент (главы, вопросы, ключевые слова)

**Никакого Python, никакого FastAPI, никакого сервера.**

## Деплой в три шага

### 1. Залить в GitHub
```bash
git init
git add .
git commit -m "init"
git branch -M main
git remote add origin https://github.com/<твой-ник>/<репо>.git
git push -u origin main
```

### 2. Включить GitHub Pages
GitHub → Settings → Pages:
- **Source:** Deploy from a branch
- **Branch:** `main`
- **Folder:** `/docs`
- Save

Через 30–60 секунд получишь URL вида `https://<твой-ник>.github.io/<репо>/`.

### 3. Прикрутить к боту через BotFather
1. Создай бота в [@BotFather](https://t.me/BotFather) (`/newbot`) — получи `BOT_TOKEN`
2. В BotFather: `/mybots` → твой бот → **Bot Settings** → **Menu Button** → **Configure menu button**
3. Введи URL твоего Pages: `https://<твой-ник>.github.io/<репо>/`
4. Название кнопки: `📖 Открыть книгу`

Всё. Открываешь бота, жмёшь кнопку меню — Mini App загружается.

## Структура

```
ПРОЕКТ КНИГА/
├── README.md
├── ТЗ.md
└── docs/                    ← GitHub Pages раздаёт отсюда
    ├── index.html           ← вёрстка Mini App
    ├── app.js               ← вся логика (грейдер + прогресс)
    ├── style.css
    └── chapters.json        ← главы и вопросы
```

## Добавить новые главы / вопросы

Правишь `docs/chapters.json`. Формат:

```json
{
  "books": [
    {
      "id": "reinert_poor_rich",
      "title": "Почему бедные страны беднеют…",
      "author": "Эрик Райнерт",
      "chapters": [
        {
          "number": 1,
          "title": "Название главы",
          "questions": [
            {
              "id": 1,
              "text": "Вопрос?",
              "reference_answer": "Развёрнутый эталон",
              "keywords": ["слово1", "ключевая фраза", "термин"],
              "required_count": 2
            }
          ]
        }
      ]
    }
  ]
}
```

После правок:
```bash
git add docs/chapters.json
git commit -m "update chapters"
git push
```

Через 30 секунд GitHub Pages подхватит изменения.

## Сброс прогресса

Написать в консоли Telegram (откроется при открытии Mini App через Telegram Desktop с DevTools):
```js
await window.Telegram.WebApp.CloudStorage.removeItem("bookreader_progress_v1");
```

Или просто удалить себя из чата с ботом и начать заново.

## Локальное тестирование

Чтобы открыть Mini App локально в браузере (без Telegram — прогресс уйдёт в localStorage):

```bash
cd docs
python3 -m http.server 8000
# открой http://localhost:8000
```

Функционал Telegram (CloudStorage, BackButton) работать не будет, но UI и грейдер проверишь.
