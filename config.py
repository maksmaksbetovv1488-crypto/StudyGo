"""StudyGo — configuration from environment variables."""

import os

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
CHANNEL_ID = os.getenv("CHANNEL_ID", "")
DATABASE_URL = os.getenv("DATABASE_URL", "")
PORT = int(os.getenv("PORT", "10000"))

# ADMIN_ID can be one id or comma-separated: 123,456
_raw = os.getenv("ADMIN_ID", "0") or "0"
ADMIN_IDS = set()
for part in _raw.replace(" ", "").split(","):
    if part.isdigit():
        ADMIN_IDS.add(int(part))
ADMIN_ID = next(iter(ADMIN_IDS), 0)  # first for backward compat
