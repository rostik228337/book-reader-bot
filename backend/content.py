"""Загрузка контента (книги, главы, вопросы) из chapters.json."""
import json
from pathlib import Path

CONTENT_PATH = Path(__file__).parent.parent / "data" / "chapters.json"


def load_content() -> dict:
    if not CONTENT_PATH.exists():
        raise RuntimeError(f"Файл с контентом не найден: {CONTENT_PATH}")
    with CONTENT_PATH.open("r", encoding="utf-8") as f:
        data = json.load(f)
    books = data.get("books")
    if not books:
        raise RuntimeError("В chapters.json нет ни одной книги")
    for b in books:
        for key in ("id", "title", "chapters"):
            if key not in b:
                raise RuntimeError(f"В книге не хватает поля '{key}': {b.get('title')}")
    return data


def get_book(content: dict, book_id: str) -> dict | None:
    for b in content.get("books", []):
        if b["id"] == book_id:
            return b
    return None


def get_chapter(content: dict, book_id: str, chapter_num: int) -> dict | None:
    book = get_book(content, book_id)
    if not book:
        return None
    for ch in book.get("chapters", []):
        if ch["number"] == chapter_num:
            return ch
    return None
