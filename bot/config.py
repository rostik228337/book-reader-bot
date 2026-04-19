"""Конфигурация: читаем .env."""
import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

ENV_PATH = Path(__file__).parent / ".env"
load_dotenv(ENV_PATH)


@dataclass
class Config:
    bot_token: str
    openai_api_key: str | None
    use_ai_grading: bool
    admin_user_id: int


def load_config() -> Config:
    token = os.getenv("BOT_TOKEN", "").strip()
    if not token:
        raise RuntimeError(
            f"BOT_TOKEN не задан. Скопируй {ENV_PATH.parent}/.env.example → .env "
            f"и впиши токен от @BotFather."
        )
    admin_str = os.getenv("ADMIN_USER_ID", "0").strip() or "0"
    try:
        admin_id = int(admin_str)
    except ValueError:
        admin_id = 0

    return Config(
        bot_token=token,
        openai_api_key=(os.getenv("OPENAI_API_KEY", "").strip() or None),
        use_ai_grading=os.getenv("USE_AI_GRADING", "false").strip().lower() == "true",
        admin_user_id=admin_id,
    )
