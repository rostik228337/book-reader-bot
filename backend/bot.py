"""Минимальный Telegram-бот — одна кнопка WebApp."""
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    MenuButtonWebApp,
    Message,
    WebAppInfo,
)

from config import load_config

log = logging.getLogger("bot")


async def start_bot() -> None:
    config = load_config()
    bot = Bot(
        config.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()

    @dp.message(Command("start"))
    async def cmd_start(message: Message) -> None:
        kb = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(
                text="📖 Открыть приложение",
                web_app=WebAppInfo(url=config.webapp_url),
            )
        ]])
        await message.answer(
            "👋 Привет! Нажми кнопку, чтобы открыть приложение для чтения книг.",
            reply_markup=kb,
        )

    # Установить Menu Button (кнопка слева от поля ввода)
    try:
        await bot.set_chat_menu_button(
            menu_button=MenuButtonWebApp(
                text="📖 Читать",
                web_app=WebAppInfo(url=config.webapp_url),
            )
        )
        log.info("Menu Button установлена: %s", config.webapp_url)
    except Exception as e:
        log.warning("Не удалось установить Menu Button: %s", e)

    try:
        log.info("Бот запущен (polling)")
        await dp.start_polling(bot)
    finally:
        await bot.session.close()
