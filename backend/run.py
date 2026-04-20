"""Точка входа: запускает FastAPI-сервер и Telegram-бота одним процессом."""
import asyncio
import logging

import uvicorn

from bot import start_bot
from main import app
from storage import init_db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger("run")


async def main() -> None:
    await init_db()
    log.info("БД инициализирована")

    server = uvicorn.Server(
        uvicorn.Config(
            app,
            host="0.0.0.0",
            port=8000,
            log_level="info",
            # Отключаем встроенный reload, запускаем вручную
        )
    )

    bot_task = asyncio.create_task(start_bot())
    server_task = asyncio.create_task(server.serve())

    try:
        await asyncio.gather(bot_task, server_task)
    except (KeyboardInterrupt, asyncio.CancelledError):
        log.info("Завершение работы...")
    finally:
        server.should_exit = True


if __name__ == "__main__":
    asyncio.run(main())
