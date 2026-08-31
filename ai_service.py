"""StudyGo — Gemini AI calls."""

import logging
from typing import Optional

from google import genai
from google.genai import types

from config import GEMINI_API_KEY
from ai_prompt import AI_SYSTEM_PROMPT

logger = logging.getLogger("studygo.ai")

_client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None

# Актуальная модель (gemini-2.0-flash больше не доступна)
GEMINI_MODEL = "gemini-3.6-flash"


async def call_gemini(prompt: str, image_bytes: Optional[bytes] = None) -> str:
    """Send prompt (and optional image) to Gemini. Returns text answer."""
    if not _client:
        return "⚠️ Gemini API не настроен. Добавьте GEMINI_API_KEY."
    try:
        contents = []
        if image_bytes:
            contents.append(
                types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg")
            )
        contents.append(prompt)

        response = _client.models.generate_content(
            model=GEMINI_MODEL,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=AI_SYSTEM_PROMPT,
                temperature=0.2,
            ),
        )
        return response.text or "Не удалось получить ответ."
    except Exception as e:
        logger.exception("Gemini error")
        # fallback на 2.5-flash если 3.6 недоступна на ключе
        err = str(e)
        if "NOT_FOUND" in err or "404" in err:
            try:
                response = _client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=contents,
                    config=types.GenerateContentConfig(
                        system_instruction=AI_SYSTEM_PROMPT,
                        temperature=0.2,
                    ),
                )
                return response.text or "Не удалось получить ответ."
            except Exception as e2:
                return f"⚠️ Ошибка AI: {e2}"
        return f"⚠️ Ошибка AI: {e}"
