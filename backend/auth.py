"""Валидация Telegram WebApp initData через HMAC-SHA256."""
import hashlib
import hmac
import json
import time
from urllib.parse import parse_qsl, unquote


def verify_init_data(init_data_str: str, bot_token: str) -> dict | None:
    """
    Проверяет подпись Telegram initData.
    Возвращает dict с полями user (id, first_name, ...) или None при провале.
    """
    if not init_data_str:
        return None

    try:
        parsed = dict(parse_qsl(init_data_str, keep_blank_values=True))
    except Exception:
        return None

    hash_value = parsed.pop("hash", None)
    if not hash_value:
        return None

    # Проверяем свежесть данных (не старше 24 часов)
    auth_date_str = parsed.get("auth_date", "0")
    try:
        if time.time() - int(auth_date_str) > 86400:
            return None
    except (ValueError, TypeError):
        return None

    # Строка проверки: ключи отсортированы, разделены \n
    data_check_string = "\n".join(
        f"{k}={v}" for k, v in sorted(parsed.items())
    )

    # Секретный ключ = HMAC("WebAppData", bot_token)
    secret_key = hmac.new(
        b"WebAppData",
        bot_token.encode("utf-8"),
        hashlib.sha256,
    ).digest()

    # Ожидаемый хэш
    expected = hmac.new(
        secret_key,
        data_check_string.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(expected, hash_value):
        return None

    # Парсим пользователя
    user_str = parsed.get("user", "{}")
    try:
        user = json.loads(unquote(user_str))
    except Exception:
        return None

    return user
