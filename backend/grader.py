"""Оценка ответов.

Два режима:
- keywords (по умолчанию, бесплатный): лемматизация pymorphy3 + поиск ключевых слов/фраз.
- ai (опциональный): OpenAI API. Если недоступен — фоллбэк на keywords.
"""
from __future__ import annotations

import json
import logging
import re

import pymorphy3

log = logging.getLogger(__name__)
_morph = pymorphy3.MorphAnalyzer()
_WORD_RE = re.compile(r"[А-Яа-яЁёA-Za-z]+")


def _lemmatize(text: str) -> list[str]:
    tokens = _WORD_RE.findall(text.lower())
    return [_morph.parse(t)[0].normal_form for t in tokens]


def _keyword_in(answer_lemmas: list[str], keyword: str) -> bool:
    """True если все леммы ключевого слова/фразы присутствуют в ответе."""
    kw_lemmas = _lemmatize(keyword)
    if not kw_lemmas:
        return False
    return all(lem in answer_lemmas for lem in kw_lemmas)


def _grade_keywords(question: dict, user_answer: str) -> dict:
    lemmas = _lemmatize(user_answer)
    keywords: list[str] = question.get("keywords", [])
    if not keywords:
        n_words = len(lemmas)
        if n_words >= 15:
            return {"score": 2, "feedback": "✅ Развёрнутый ответ."}
        if n_words >= 5:
            return {"score": 1, "feedback": "⚠️ Ответ короткий, раскрой подробнее."}
        return {"score": 0, "feedback": "❌ Слишком коротко или пусто."}

    required = int(question.get("required_count", max(1, len(keywords) // 2)))
    matched = [kw for kw in keywords if _keyword_in(lemmas, kw)]
    missing = [kw for kw in keywords if kw not in matched]

    if len(matched) >= required:
        return {
            "score": 2,
            "feedback": f"✅ Уловил ключевые мысли. Найдено: {len(matched)}/{len(keywords)}.",
        }
    if len(matched) == required - 1:
        miss_str = ", ".join(f'«{m}»' for m in missing[:3])
        return {
            "score": 1,
            "feedback": f"⚠️ Частично. Не хватило: {miss_str}.",
        }
    ref = question.get("reference_answer", "")
    ref_snippet = ref[:220] + ("..." if len(ref) > 220 else "")
    miss_str = ", ".join(f'«{m}»' for m in missing[:4])
    tail = f"\n\nЭталон: {ref_snippet}" if ref_snippet else ""
    return {
        "score": 0,
        "feedback": f"❌ Ключевые смыслы упущены: {miss_str}.{tail}",
    }


_ai_client = None


async def _grade_ai(question: dict, user_answer: str, api_key: str) -> dict:
    global _ai_client
    if _ai_client is None:
        from openai import AsyncOpenAI
        _ai_client = AsyncOpenAI(api_key=api_key)

    system = (
        "Ты — строгий, но справедливый преподаватель. Оцени, насколько ответ студента "
        "совпадает по СМЫСЛУ с эталонным ответом. Верни СТРОГО JSON: "
        '{"score": 0|1|2, "feedback": "комментарий на русском, 1-2 предложения"}. '
        "0 — мимо, 1 — уловил часть, 2 — правильный ответ по сути."
    )
    user = (
        f"Вопрос: {question.get('text', '')}\n\n"
        f"Эталонный ответ: {question.get('reference_answer', '')}\n\n"
        f"Ответ студента: {user_answer}"
    )
    resp = await _ai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        response_format={"type": "json_object"},
        temperature=0.2,
    )
    data = json.loads(resp.choices[0].message.content)
    score = max(0, min(2, int(data.get("score", 0))))
    feedback = str(data.get("feedback", "")).strip() or "Оценено."
    return {"score": score, "feedback": feedback}


async def grade_answer(
    question: dict,
    user_answer: str,
    use_ai: bool = False,
    api_key: str | None = None,
) -> dict:
    """Возвращает {'score': 0|1|2, 'feedback': str}."""
    if not user_answer or not user_answer.strip():
        return {"score": 0, "feedback": "❌ Пустой ответ."}

    if use_ai and api_key:
        try:
            return await _grade_ai(question, user_answer, api_key)
        except Exception as e:
            log.warning(f"AI-оценка упала, откат на keywords: {e}")
    return _grade_keywords(question, user_answer)
