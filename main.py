"""StudyGo — entry point"""

import asyncio
import logging
import threading

from flask import Flask
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN, PORT
from database import init_db
from handlers import setup_routers

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("studygo")

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())
dp.include_router(setup_routers())
flask_app = Flask(__name__)


@flask_app.route("/")
def health():
    return "StudyGo is running"


async def on_startup():
    logger.info("Initializing database...")
    init_db()
    logger.info("StudyGo started")


async def run_bot():
    await on_startup()
    await dp.start_polling(bot)


def run_flask():
    flask_app.run(host="0.0.0.0", port=PORT, threaded=True)


if __name__ == "__main__":
    t = threading.Thread(target=run_flask, daemon=True)
    t.start()
    asyncio.run(run_bot())
