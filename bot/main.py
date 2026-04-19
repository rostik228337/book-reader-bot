"""Telegram-бот для осмысленного чтения книг. Точка входа."""
import asyncio
import html
import logging

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ChatAction, ParseMode
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import CallbackQuery, ErrorEvent, Message

from config import load_config
from content import get_book, get_chapter, load_content
from grader import grade_answer
from keyboards import (
    chapters_kb,
    confirm_reset_kb,
    main_menu_kb,
    result_kb,
    start_chapter_kb,
)
from storage import (
    ensure_user,
    get_stats,
    get_user_progress,
    init_db,
    reset_user,
    save_attempt,
    upsert_chapter_progress,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger("bot")

PASS_THRESHOLD = 1.5


class Quiz(StatesGroup):
    answering = State()


config = load_config()
content = load_content()

dp = Dispatcher(storage=MemoryStorage())


def esc(s: str) -> str:
    """HTML-escape текста пользователя."""
    return html.escape(s or "", quote=False)


# ─── Команды ───────────────────────────────────────────────────────────────

@dp.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    await ensure_user(message.from_user.id, message.from_user.username)
    books = content["books"]
    await message.answer(
        "👋 Привет! Это бот для осмысленного чтения.\n\n"
        "После каждой главы отвечаешь на 3–7 открытых вопросов — "
        "бот проверяет и решает, пропустить дальше или перечитать.\n\n"
        "Команды: /stats — статистика, /reset — сброс (только для админа).\n\n"
        "<b>Выбери книгу:</b>",
        reply_markup=main_menu_kb(books),
    )


@dp.message(Command("stats"))
async def cmd_stats(message: Message) -> None:
    s = await get_stats(message.from_user.id)
    await message.answer(
        "📊 <b>Статистика</b>\n\n"
        f"Пройдено глав: {s['completed_chapters']}\n"
        f"Средний балл: {s['avg_score']:.2f}"
    )


@dp.message(Command("reset"))
async def cmd_reset(message: Message) -> None:
    if message.from_user.id != config.admin_user_id:
        await message.answer("⛔ Команда недоступна.")
        return
    await message.answer(
        "Уверен? Это удалит весь прогресс.",
        reply_markup=confirm_reset_kb(),
    )


# ─── Навигация ─────────────────────────────────────────────────────────────

@dp.callback_query(F.data == "menu")
async def cb_menu(cb: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await cb.message.edit_text(
        "<b>Выбери книгу:</b>",
        reply_markup=main_menu_kb(content["books"]),
    )
    await cb.answer()


@dp.callback_query(F.data == "reset_confirm")
async def cb_reset_confirm(cb: CallbackQuery) -> None:
    if cb.from_user.id != config.admin_user_id:
        await cb.answer("⛔", show_alert=True)
        return
    await reset_user(cb.from_user.id)
    await cb.message.edit_text("✅ Прогресс сброшен. /start — начать заново.")
    await cb.answer()


@dp.callback_query(F.data.startswith("book:"))
async def cb_book(cb: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    book_id = cb.data.split(":", 1)[1]
    book = get_book(content, book_id)
    if not book:
        await cb.answer("Книга не найдена", show_alert=True)
        return
    progress = await get_user_progress(cb.from_user.id, book_id)
    text = (
        f"📖 <b>{esc(book['title'])}</b>\n"
        f"<i>{esc(book.get('author', ''))}</i>\n\n"
        f"Выбери главу:"
    )
    await cb.message.edit_text(
        text,
        reply_markup=chapters_kb(book_id, book["chapters"], progress),
    )
    await cb.answer()


@dp.callback_query(F.data.startswith("locked:"))
async def cb_locked(cb: CallbackQuery) -> None:
    await cb.answer("Сначала пройди предыдущую главу.", show_alert=True)


@dp.callback_query(F.data.startswith("chap:"))
async def cb_chapter(cb: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    _, book_id, num_str = cb.data.split(":")
    num = int(num_str)
    chapter = get_chapter(content, book_id, num)
    if not chapter:
        await cb.answer("Главы нет", show_alert=True)
        return
    qs = chapter.get("questions", [])
    if not qs:
        await cb.answer(
            "В этой главе пока нет вопросов. Добавь их в chapters.json.",
            show_alert=True,
        )
        return
    await cb.message.edit_text(
        f"📚 <b>Глава {num}. {esc(chapter['title'])}</b>\n\n"
        f"Вопросов: {len(qs)}\n"
        f"Отвечай текстом, своими словами. В конце — оценка по каждому.",
        reply_markup=start_chapter_kb(book_id, num),
    )
    await cb.answer()


@dp.callback_query(F.data.startswith("start:"))
async def cb_start_quiz(cb: CallbackQuery, state: FSMContext) -> None:
    _, book_id, num_str = cb.data.split(":")
    num = int(num_str)
    chapter = get_chapter(content, book_id, num)
    if not chapter or not chapter.get("questions"):
        await cb.answer("Нет вопросов", show_alert=True)
        return
    await state.set_state(Quiz.answering)
    await state.update_data(
        book_id=book_id,
        chapter_num=num,
        question_index=0,
        results=[],
    )
    first_q = chapter["questions"][0]
    total = len(chapter["questions"])
    await cb.message.answer(
        f"❓ <b>Вопрос 1/{total}</b>\n\n{esc(first_q['text'])}"
    )
    await cb.answer()


# ─── Приём ответов ─────────────────────────────────────────────────────────

@dp.message(Quiz.answering, F.text)
async def on_answer(message: Message, state: FSMContext, bot: Bot) -> None:
    data = await state.get_data()
    book_id: str = data["book_id"]
    num: int = data["chapter_num"]
    idx: int = data["question_index"]
    results: list[dict] = data["results"]

    chapter = get_chapter(content, book_id, num)
    if not chapter:
        await state.clear()
        await message.answer("Глава исчезла 🤔 Напиши /start.")
        return
    questions: list[dict] = chapter["questions"]
    q = questions[idx]

    await bot.send_chat_action(message.chat.id, ChatAction.TYPING)

    try:
        verdict = await grade_answer(
            q,
            message.text,
            use_ai=config.use_ai_grading,
            api_key=config.openai_api_key,
        )
    except Exception:
        log.exception("Grader failed")
        verdict = {"score": 0, "feedback": "Ошибка при оценке, засчитано 0."}

    await save_attempt(
        message.from_user.id,
        book_id,
        num,
        q["id"],
        message.text,
        verdict["score"],
        verdict["feedback"],
    )
    results.append({
        "question": q["text"],
        "answer": message.text,
        "score": verdict["score"],
        "feedback": verdict["feedback"],
    })

    idx += 1
    if idx < len(questions):
        await state.update_data(question_index=idx, results=results)
        next_q = questions[idx]
        await message.answer(
            f"❓ <b>Вопрос {idx + 1}/{len(questions)}</b>\n\n{esc(next_q['text'])}"
        )
        return

    # ─── Все вопросы пройдены — итог ───
    await state.clear()

    total_score = sum(r["score"] for r in results)
    avg = total_score / len(results)
    max_total = len(results) * 2
    passed = avg >= PASS_THRESHOLD

    await upsert_chapter_progress(message.from_user.id, book_id, num, avg)

    book = get_book(content, book_id)
    has_next = bool(book) and any(
        c["number"] == num + 1 for c in book["chapters"]
    )

    # Итоговое сообщение — с защитой от переполнения 4096 символов
    header = (
        f"{'🎉' if passed else '📚'} <b>Итог главы {num}</b>\n"
        f"Балл: <b>{total_score}/{max_total}</b> (среднее {avg:.2f})\n"
    )
    await message.answer(header)

    for i, r in enumerate(results, 1):
        emoji = {0: "❌", 1: "⚠️", 2: "✅"}[r["score"]]
        answer_preview = r["answer"][:300] + ("…" if len(r["answer"]) > 300 else "")
        block = (
            f"<b>{i}. {emoji} {r['score']}/2</b>\n"
            f"<i>{esc(r['question'])}</i>\n\n"
            f"<b>Твой ответ:</b> {esc(answer_preview)}\n\n"
            f"<b>Фидбек:</b> {esc(r['feedback'])}"
        )
        await message.answer(block)

    footer_text = (
        "✅ <b>Глава пройдена!</b> Можно переходить дальше."
        if passed
        else "📖 <b>Нужно перечитать.</b> Смыслы уложатся при повторе."
    )
    await message.answer(
        footer_text,
        reply_markup=result_kb(book_id, num, passed, has_next),
    )


@dp.message(Quiz.answering)
async def on_nontext(message: Message) -> None:
    await message.answer("Нужен текстовый ответ. Напиши мысль словами.")


# ─── Глобальный обработчик ошибок ──────────────────────────────────────────

@dp.errors()
async def on_error(event: ErrorEvent) -> bool:
    log.exception(f"Unhandled error: {event.exception}")
    try:
        if event.update.message:
            await event.update.message.answer(
                "Что-то пошло не так 😵 Попробуй ещё раз или /start."
            )
        elif event.update.callback_query:
            await event.update.callback_query.answer(
                "Что-то пошло не так, попробуй ещё раз.",
                show_alert=True,
            )
    except Exception:
        pass
    return True


# ─── Запуск ────────────────────────────────────────────────────────────────

async def main() -> None:
    await init_db()
    bot = Bot(
        config.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    log.info(
        "Бот запущен (polling). AI-оценка: %s",
        "ON" if (config.use_ai_grading and config.openai_api_key) else "OFF",
    )
    try:
        await dp.start_polling(bot)
    finally:
    