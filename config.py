"""StudyGo — configuration from environment variables."""

import os

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0") or "0")
CHANNEL_ID = os.getenv("CHANNEL_ID", "")  # @channel or -100...
DATABASE_URL = os.getenv("DATABASE_URL", "")
PORT = int(os.getenv("PORT", "10000"))
