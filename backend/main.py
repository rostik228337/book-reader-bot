"""FastAPI-бэкенд: API-роуты + раздача статики webapp/."""
import logging
import os
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from auth import verify_init_data
from config import load_config
from content import get_book, get_chapter, load_content
from grader import grade_answer
from storage import (
    ensure_user,
    get_total_progress,
    get_user_progress,
    mark_chapter_passed,
    save_attempt,
)

log = logging.getLogger("api")

BASE_DIR = Path(__file__).parent.parent
WEBAPP_DIR = BASE_DIR / "webapp"

app = FastAPI(title="BookReader Mini App")

# ─── Статика ────────────────────────────────────────────────────────────────

app.mount("/static", StaticFiles(directory=str(WEBAPP_DIR)), name="static")


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def serve_index():
    return FileResponse(WEBAPP_DIR / "index.html")


@app.get("/app.js", include_in_schema=False)
async def serve_js():
    return FileResponse(WEBAPP_DIR / "app.js", media_type="application/javascript")


@app.get("/style.css", include_in_schema=False)
async def serve_css():
    return FileResponse(WEBAPP_DIR / "style.css", media_type="text/css")


# ─── Авторизация ────────────────────────────────────────────────────────────

_config = load_config()
_content = load_content()


def verify_user(x_telegram_init_data: Annotated[str | None, Header()] = None) -> dict:
    if not x_telegram_init_data:
        raise HTTPException(status_code=401, detail="Missing initData")
    user = verify_init_data(x_telegram_init_data, _config.bot_token)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid initData")
    return user


# ─── Модели запросов ────────────────────────────────────────────────────────

class InitRequest(BaseModel):
    initData: str


class AnswerRequest(BaseModel):
    book_id: str
    chapter_num: int
    question_id: int
    answer_text: str


class CompleteChapterRequest(BaseModel):
    book_id: str
    chapter_num: int
    scores: list[int]


# ─── API роуты ──────────────────────────────────────────────────────────────

@app.post("/api/init")
async def api_init(body: InitRequest):
    """Инициализация: проверяет initData, возвращает книги + прогресс."""
    user = verify_init_data(body.initData, _config.bot_token)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid initData")

    user_id = user.get("id")
    username = user.get("username") or user.get("first_name")
    await ensure_user(user_id, username)

    books_out = []
    for book in _content["books"]:
        total_chapters = len(book["chapters"])
        progress = await get_user_progress(user_id, book["id"])
        percent = await get_total_progress(user_id, book["id"], total_chapters)

        chapters_out = []
        prev_completed = True
        for ch in book["chapters"]:
            num = ch["number"]
            p = progress.get(num, {"avg": 0, "completed": False})
            if p["completed"]:
                status = "completed"
            elif prev_completed:
                status = "available"
            else:
                status = "locked"
            chapters_out.append({
                "number": num,
                "title": ch["title"],
                "status": status,
                "question_count": len(ch.get("questions", [])),
            })
            prev_completed = p["completed"]

        books_out.append({
            "id": book["id"],
            "title": book["title"],
            "author": book.get("author", ""),
            "total_chapters": total_chapters,
            "progress_percent": percent,
            "chapters": chapters_out,
        })

    return {
        "user": {
            "id": user_id,
            "first_name": user.get("first_name", ""),
        },
        "books": books_out,
    }


@app.get("/api/book/{book_id}/chapters")
async def api_chapters(book_id: str, user: dict = Depends(verify_user)):
    user_id = user["id"]
    book = get_book(_content, book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    total_chapters = len(book["chapters"])
    progress = await get_user_progress(user_id, book_id)
    percent = await get_total_progress(user_id, book_id, total_chapters)

    chapters_out = []
    prev_completed = True
    for ch in book["chapters"]:
        num = ch["number"]
        p = progress.get(num, {"avg": 0, "completed": False})
        if p["completed"]:
            status = "completed"
        elif prev_completed:
            status = "available"
        else:
            status = "locked"
        chapters_out.append({
            "number": num,
            "title": ch["title"],
            "status": status,
            "question_count": len(ch.get("questions", [])),
        })
        prev_completed = p["completed"]

    return {
        "book_id": book_id,
        "title": book["title"],
        "author": book.get("author", ""),
        "progress_percent": percent,
        "chapters": chapters_out,
    }


@app.get("/api/chapter/{book_id}/{chapter_num}")
async def api_chapter(book_id: str, chapter_num: int, user: dict = Depends(verify_user)):
    chapter = get_chapter(_content, book_id, chapter_num)
    if not chapter:
        raise HTTPException(status_code=404, detail="Chapter not found")

    # Отдаём вопросы без keywords и reference_answer
    questions = [
        {"id": q["id"], "text": q["text"]}
        for q in chapter.get("questions", [])
    ]
    return {
        "number": chapter_num,
        "title": chapter["title"],
        "questions": questions,
    }


@app.post("/api/answer")
async def api_answer(body: AnswerRequest, user: dict = Depends(verify_user)):
    user_id = user["id"]
    chapter = get_chapter(_content, body.book_id, body.chapter_num)
    if not chapter:
        raise HTTPException(status_code=404, detail="Chapter not found")

    # Найти вопрос
    question = next(
        (q for q in chapter.get("questions", []) if q["id"] == body.question_id),
        None,
    )
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    verdict = await grade_answer(
        question,
        body.answer_text,
        use_ai=_config.use_ai_grading,
        api_key=_config.openai_api_key,
    )

    await save_attempt(
        user_id,
        body.book_id,
        body.chapter_num,
        body.question_id,
        body.answer_text,
        verdict["score"],
        verdict["feedback"],
    )

    return {"score": verdict["score"], "feedback": verdict["feedback"]}


@app.post("/api/complete_chapter")
async def api_complete_chapter(
    body: CompleteChapterRequest, user: dict = Depends(verify_user)
):
    user_id = user["id"]
    book = get_book(_content, body.book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    all_perfect = bool(body.scores) and all(s == 2 for s in body.scores)

    if all_perfect:
        await mark_chapter_passed(user_id, body.book_id, body.chapter_num)

    total_chapters = len(book["chapters"])
    total_percent = await get_total_progress(user_id, body.book_id, total_chapters)

    # Проверяем открылась ли следующая глава
    next_chapter_exists = any(
        c["number"] == body.chapter_num + 1 for c in book["chapters"]
    )

    return {
        "passed": all_perfect,
        "total_percent": total_percent,
        "next_chapter_unlocked": all_perfect and next_chapter_exists,
    }
