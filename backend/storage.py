"""SQLite-хранилище прогресса."""
from pathlib import Path

import aiosqlite

DB_PATH = Path(__file__).parent.parent / "data" / "progress.db"


async def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS attempts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                book_id TEXT NOT NULL,
                chapter_num INTEGER NOT NULL,
                question_id INTEGER NOT NULL,
                answer_text TEXT NOT NULL,
                score INTEGER NOT NULL,
                feedback TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS chapter_progress (
                user_id INTEGER NOT NULL,
                book_id TEXT NOT NULL,
                chapter_num INTEGER NOT NULL,
                best_avg_score REAL NOT NULL DEFAULT 0,
                completed INTEGER NOT NULL DEFAULT 0,
                completed_at TEXT,
                PRIMARY KEY (user_id, book_id, chapter_num)
            );
            """
        )
        await db.commit()


async def ensure_user(user_id: int, username: str | None) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO users(user_id, username) VALUES (?, ?)",
            (user_id, username),
        )
        await db.commit()


async def save_attempt(
    user_id: int,
    book_id: str,
    chapter_num: int,
    question_id: int,
    answer_text: str,
    score: int,
    feedback: str,
) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO attempts(user_id, book_id, chapter_num, question_id, "
            "answer_text, score, feedback) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (user_id, book_id, chapter_num, question_id, answer_text, score, feedback),
        )
        await db.commit()


async def mark_chapter_passed(user_id: int, book_id: str, chapter_num: int) -> None:
    """Отметить главу как пройденную (все ответы = 2 балла)."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO chapter_progress(user_id, book_id, chapter_num, best_avg_score, completed, completed_at)
            VALUES (?, ?, ?, 2.0, 1, datetime('now'))
            ON CONFLICT(user_id, book_id, chapter_num)
            DO UPDATE SET best_avg_score=2.0, completed=1,
                completed_at=COALESCE(completed_at, datetime('now'))
            """,
            (user_id, book_id, chapter_num),
        )
        await db.commit()


async def get_user_progress(user_id: int, book_id: str) -> dict[int, dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT chapter_num, best_avg_score, completed FROM chapter_progress "
            "WHERE user_id=? AND book_id=?",
            (user_id, book_id),
        )
        rows = await cur.fetchall()
    return {r[0]: {"avg": r[1], "completed": bool(r[2])} for r in rows}


async def get_total_progress(user_id: int, book_id: str, total_chapters: int) -> float:
    """Возвращает процент пройденных глав (0.0–100.0)."""
    if total_chapters == 0:
        return 0.0
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT COUNT(*) FROM chapter_progress "
            "WHERE user_id=? AND book_id=? AND completed=1",
            (user_id, book_id),
        )
        row = await cur.fetchone()
    completed = row[0] if row else 0
    return round((completed / total_chapters) * 100, 1)


async def get_stats(user_id: int) -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT COUNT(*), COALESCE(AVG(best_avg_score), 0) "
            "FROM chapter_progress WHERE user_id=? AND completed=1",
            (user_id,),
        )
        row = await cur.fetchone()
    return {
        "completed_chapters": (row[0] if row else 0) or 0,
        "avg_score": (row[1] if row else 0.0) or 0.0,
    }
