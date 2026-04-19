"""Инлайн-клавиатуры."""
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def main_menu_kb(books: list[dict]) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=f"📖 {b['title']}", callback_data=f"book:{b['id']}")]
        for b in books
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def chapters_kb(
    book_id: str, chapters: list[dict], progress: dict[int, dict]
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    prev_completed = True  # первая глава всегда открыта
    for ch in chapters:
        num = ch["number"]
        p = progress.get(num, {"completed": False})
        if p["completed"]:
            emoji = "✅"
            cb = f"chap:{book_id}:{num}"
        elif prev_completed:
            emoji = "🔓"
            cb = f"chap:{book_id}:{num}"
        else:
            emoji = "🔒"
            cb = f"locked:{book_id}:{num}"
        rows.append([
            InlineKeyboardButton(
                text=f"{emoji} Гл. {num}. {ch['title']}",
                callback_data=cb,
            )
        ])
        prev_completed = bool(p.get("completed"))
    rows.append([
        InlineKeyboardButton(text="⬅️ К списку книг", callback_data="menu")
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def start_chapter_kb(book_id: str, chapter_num: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚀 Поехали", callback_data=f"start:{book_id}:{chapter_num}")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data=f"book:{book_id}")],
    ])


def result_kb(
    book_id: str, chapter_num: int, passed: bool, has_next: bool
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    if passed and has_next:
        rows.append([InlineKeyboardButton(
            text="➡️ Следующая глава",
            callback_data=f"chap:{book_id}:{chapter_num + 1}",
        )])
    if not passed:
        rows.append([InlineKeyboardButton(
            text="🔁 Перечитать и попробовать снова",
            callback_data=f"chap:{book_id}:{chapter_num}",
        )])
    rows.append([InlineKeyboardButton(
        text="📚 К списку глав", callback_data=f"book:{book_id}"
    )])
    rows.append([InlineKeyboardButton(text="🏠 В меню", callback_data="menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def confirm_reset_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚠️ Да, сбросить", callback_data="reset_confirm")],
        [InlineKeyboardButton(text="Отмена", callback_data="menu")],
    ])
