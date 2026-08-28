import os
import asyncio
import threading
import logging
from datetime import datetime, timedelta

from flask import Flask

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    LabeledPrice,
    PreCheckoutQuery,
)

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from google import genai
from google.genai import types

from database import (
    init_db,
    get_or_create_user,
    get_user,
    get_xp,
    add_xp,
    spend_xp,
    add_score,
    is_premium,
    add_premium,
    save_premium_purchase,
    save_stars_transaction,
    create_referral,
    verify_referral,
    reward_referral,
    save_subscription_status,
    is_channel_subscribed,
    get_daily_rank,
    get_user_daily_rank,
    save_daily_rank,
    log_ai_usage,
    add_admin_log,
    set_blocked,
    is_blocked,
    get_setting_int,
    get_total_users,
    get_total_premium_users,
    get_total_xp,
    get_referral_count,
    increment_task_count,
    increment_photo_count,
)


# ============================================================
# CONFIG
# ============================================================

BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")

ADMIN_ID = int(
    os.getenv("ADMIN_ID", "123456789")
)

CHANNEL_USERNAME = os.getenv(
    "CHANNEL_USERNAME",
    "@YOUR_CHANNEL"
)

GEMINI_API_KEY = os.getenv(
    "GEMINI_API_KEY",
    ""
)

PORT = int(
    os.getenv("PORT", "10000")
)

BOT_USERNAME = os.getenv(
    "BOT_USERNAME",
    ""
)


# ============================================================
# LOGGING
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

logger = logging.getLogger("StudyGo")


# ============================================================
# TELEGRAM + AI
# ============================================================

bot = Bot(
    token=BOT_TOKEN
)

dp = Dispatcher()

scheduler = AsyncIOScheduler(
    timezone="Asia/Almaty"
)

ai_client = None

if GEMINI_API_KEY:
    ai_client = genai.Client(
        api_key=GEMINI_API_KEY
    )


# ============================================================
# FLASK
# ============================================================

app = Flask(__name__)


@app.route("/")
def home():
    return "StudyGo is running!"


@app.route("/health")
def health():
    return {
        "status": "ok",
        "bot": "StudyGo"
    }


def run_flask():
    app.run(
        host="0.0.0.0",
        port=PORT,
        use_reloader=False
    )


# ============================================================
# KEYBOARDS
# ============================================================

def main_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🧠 Решить задание",
                    callback_data="solve"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📚 Объяснить тему",
                    callback_data="explain"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📝 Тест",
                    callback_data="test"
                )
            ],
            [
                InlineKeyboardButton(
                    text="👤# ============================================================
# SUBSCRIPTION
# ============================================================

async def check_channel_subscription(user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(
            chat_id=CHANNEL_USERNAME,
            user_id=user_id
        )

        subscribed = member.status in (
            "member",
            "administrator",
            "creator"
        )

        save_subscription_status(
            user_id,
            subscribed
        )

        return subscribed

    except Exception as e:
        logger.warning(
            "Не удалось проверить подписку: %s",
            e
        )
        return False


async def verify_user_referral(user_id: int):
    subscribed = await check_channel_subscription(
        user_id
    )

    if not subscribed:
        return False

    referrer_id = verify_referral(user_id)

    if referrer_id:
        reward_referral(
            referrer_id,
            user_id
        )

    return True


# ============================================================
# PROFILE
# ============================================================

@dp.callback_query(F.data == "profile")
async def profile_handler(callback: CallbackQuery):

    user_id = callback.from_user.id
    user = get_user(user_id)

    if not user:
        get_or_create_user(
            user_id,
            callback.from_user.username,
            callback.from_user.first_name
        )
        user = get_user(user_id)

    xp = user[3]
    score = user[4]
    level = user[6]
    premium = is_premium(user_id)
    referrals = get_referral_count(user_id)

    premium_text = (
        "💎 Активен"
        if premium
        else "❌ Нет"
    )

    rank = get_user_daily_rank(user_id)

    await callback.message.edit_text(
        "👤 <b>ТВОЙ ПРОФИЛЬ</b>\n\n"
        f"⭐ XP: <b>{xp}</b>\n"
        f"🏆 Очки: <b>{score}</b>\n"
        f"📈 Уровень: <b>{level}</b>\n"
        f"💎 Premium: <b>{premium_text}</b>\n"
        f"👥 Рефералы: <b>{referrals}</b>\n"
        f"🥇 Место сегодня: <b>{rank or '—'}</b>\n",
        reply_markup=back_keyboard(),
        parse_mode="HTML"
    )

    await callback.answer()


# ============================================================
# XP
# ============================================================

def xp_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="⭐ 100 XP — 10 ⭐",
                    callback_data="xp_100"
                )
            ],
            [
                InlineKeyboardButton(
                    text="⭐ 500 XP — 50 ⭐",
                    callback_data="xp_500"
                )
            ],
            [
                InlineKeyboardButton(
                    text="⭐ 1000 XP — 100 ⭐",
                    callback_data="xp_1000"
                )
            ],
            [
                InlineKeyboardButton(
                    text="◀️ Назад",
                    callback_data="back"
                )
            ]
        ]
    )


@dp.callback_query(F.data == "xp")
async def xp_handler(callback: CallbackQuery):

    xp = get_xp(
        callback.from_user.id
    )

    await callback.message.edit_text(
        "⭐ <b>XP</b>\n\n"
        f"Твой баланс: <b>{xp} XP</b>\n\n"
        "💰 Курс:\n"
        "<b>1 ⭐ = 10 XP</b>\n\n"
        "XP можно получить:\n"
        "• за задания\n"
        "• за ежедневную активность\n"
        "• за еженедельные задания\n"
        "• за рефералов\n"
        "• за Telegram Stars",
        reply_markup=xp_keyboard(),
        parse_mode="HTML"
    )

    await callback.answer()


# ============================================================
# PREMIUM
# ============================================================

@dp.callback_query(F.data ==# ============================================================
# XP COSTS
# ============================================================

def get_request_cost(mode, is_photo=False):

    if is_photo:
        return get_setting_int(
            "ai_photo",
            30
        )

    costs = {
        "solve": 20,
        "explain": 20,
        "test": 30,
        "chat": 10
    }

    return costs.get(
        mode,
        10
    )


async def process_ai_request(
    message: Message,
    text: str,
    mode: str,
    image_bytes=None,
    mime_type="image/jpeg"
):

    user_id = message.from_user.id

    if is_blocked(user_id):
        await message.answer(
            "🚫 Ваш аккаунт заблокирован."
        )
        return

    premium = is_premium(user_id)

    cost = get_request_cost(
        mode,
        image_bytes is not None
    )

    # Premium не тратит XP
    if not premium:

        if get_xp(user_id) < cost:
            await message.answer(
                "❌ Недостаточно XP.\n\n"
                f"Стоимость запроса: <b>{cost} XP</b>\n"
                f"Твой баланс: <b>{get_xp(user_id)} XP</b>\n\n"
                "XP можно получить через задания, "
                "рефералов или Telegram Stars.",
                parse_mode="HTML"
            )
            return

        if not spend_xp(
            user_id,
            cost,
            f"AI-запрос: {mode}"
        ):
            await message.answer(
                "❌ Не удалось списать XP. "
                "Попробуй ещё раз."
            )
            return

    await message.bot.send_chat_action(
        message.chat.id,
        "typing"
    )

    prompt = get_ai_prompt(
        text,
        mode
    )

    answer = await ask_ai(
        prompt,
        image_bytes,
        mime_type
    )

    log_ai_usage(
        user_id,
        mode,
        cost if not premium else 0,
        True
    )

    add_score(
        user_id,
        5,
        daily=True
    )

    await message.answer(
        "💎 <b>PREMIUM</b>\n\n" + answer
        if premium
        else answer,
        parse_mode="HTML"
    )


# ============================================================
# TEXT MESSAGES
# ============================================================

@dp.message(F.text)
async def text_handler(message: Message):

    if not message.from_user:
        return

    user_id = message.from_user.id

    get_or_create_user(
        user_id,
        message.from_user.username,
        message.from_user.first_name
    )

    if is_blocked(user_id):
        await message.answer(
            "🚫 Ваш аккаунт заблокирован."
        )
        return

    text = message.text.strip()

    if text.startswith("/"):
        return

    mode = user_modes.get(
        user_id,
        "chat"
    )

    await process_ai_request(
        message,
        text,
        mode
    )


# ============================================================
# PHOTO
# ============================================================

@dp.message(F.photo)
async def photo_handler(message: Message):

    if not message.from_user:
        return

    user_id = message.from_user.id

    get_or_create_user(
        user_id,
        message.from_user.username,
        message.from_user.first_name
    )

    if is_blocked(user_id):
        await message.answer(
            "🚫 Ваш аккаунт заблокирован."
        )
        return

    photo = message.photo[-1]

    file = await bot.get_file(
        photo.file_id
    )

    from io import BytesIO

    buffer = BytesIO()

    await bot.download_file(
        file.file_path,
        buffer
    )

    image_bytes = buffer.getvalue()

    mode = user_modes.get(
        user_id,
        "solve"
    )

    caption = (
        message.caption
        or
        "Реши задание на фотографии. "
        "Сначала внимательно распознай изображение."
    )

    increment_photo_count(
        user_id
    )

    await process_ai_request(
        message,
        caption,
        mode,
        image_bytes,
        "image/jpeg"
    )


# ============================================================
# TASKS
# ============================================================

@dp.callback_query(F.data == "tasks")
async def tasks_handler(callback: CallbackQuery):

    user_id = callback.from_user.id

    await callback.message.edit_text(
        "🎯 <b>ЗАДАНИЯ STUDYGO</b>\n\n"
        "☀️ Ежедневные:\n"
        "• Решить 3 задания — +30 XP\n"
        "• Изучить тему — +20 XP\n"
        "• Зайти в бота — +10 XP\n\n"
        "📅 Еженедельные:\n"
        "• Выполнить 20 заданий — +200 XP\n"
        "• Набрать 100 очков — +100 XP\n\n"
        "💡 Выполняй задания регулярно, "
        "чтобы получать XP и попадать "
        "в рейтинг.",
        reply_markup=back_keyboard(),
        parse_mode="HTML"
    )

    await callback.answer()


# ============================================================
# RATING
# ============================================================

@dp.callback_query(F.data == "rating")
async def rating_handler(callback: CallbackQuery):

    rows = get_daily_rank(30)

    if not rows:
        await callback.message.edit_text(
            "🏆 Пока рейтинг пуст.",
            reply_markup=back_keyboard()
        )
        await callback.answer()
        return

    text = (
        "🏆 <b>ЕЖЕДНЕВНЫЙ РЕЙТИНГ</b>\n\n"
    )

    medals = {
        1: "🥇",
        2: "🥈",
        3: "🥉"
    }

    for position, row in enumerate(rows, 1):

        user_id = row[0]
        username = row[1]
        first_name = row[2]
        daily_score = row[3]

        name = (
            f"@{username}"
            if username
            else first_name or str(user_id)
        )

        medal = medals.get(
            position,
            f"{position}."
        )

        text += (
            f"{medal} <b>{name}</b> — "
            f"{daily_score} очков\n"
        )

    text += (
        "\n🎁 Награды:\n"
        "🥇 1 место — 100 XP\n"
        "🥈 2 место — 70 XP\n"
        "🥉 3 место — 50 XP\n"
        "\nРейтинг обновляется каждый день."
    )

    await callback.message.edit_text(
        text,
        reply_markup=back_keyboard(),
        parse_mode="HTML"
    )

    await callback.answer()


# ============================================================
# REFERRALS
# ============================================================

@dp.callback_query(F.data == "referrals")
async def referrals_handler(callback: CallbackQuery):

    user_id = callback.from_user.id

    bot_info = await bot.get_me()

    referral_link = (
        f"https://t.me/{bot_info.username}"
        f"?start=ref_{user_id}"
    )

    count = get_referral_count(
        user_id
    )

    await callback.message.edit_text(
        "👥 <b>РЕФЕРАЛЬНАЯ СИСТЕМА</b>\n\n"
        f"Успешных рефералов: <b>{count}</b>\n\n"
        "🎁 За нового пользователя:\n"
        "• Пригласивший получает <b>100 XP</b>\n"
        "• Новый пользователь получает <b>20 XP</b>\n\n"
        "⚠️ Реферал засчитывается после "
        "подписки на наш Telegram-канал.\n\n"
        f"🔗 Твоя ссылка:\n<code>{referral_link}</code>",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="✅ Проверить подписку",
                        callback_data="verify_ref"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="◀️ Назад",
                        callback_data="back"
                    )
                ]
            ]
        ),
        parse_mode="HTML"
    )

    await callback.answer()


@dp.callback_query(F.data == "verify_ref")
async def verify_ref_handler(callback: CallbackQuery):

    success = await verify_user_referral(
        callback.from_user.id
    )

    if success:
        await callback.answer(
            "✅ Подписка подтверждена!",
            show_alert=True
        )
    else:
        await callback.answer(
            "❌ Сначала подпишись на канал.",
            show_alert=True# ============================================================
# TELEGRAM STARS — XP
# ============================================================

XP_PACKAGES = {
    "100": 100,
    "500": 500,
    "1000": 1000
}


@dp.callback_query(F.data.startswith("xp_"))
async def xp_purchase_handler(
    callback: CallbackQuery
):

    package = callback.data.replace(
        "xp_",
        ""
    )

    if package not in XP_PACKAGES:
        await callback.answer(
            "❌ Неизвестный пакет.",
            show_alert=True
        )
        return

    xp_amount = XP_PACKAGES[package]

    # 1 ⭐ = 10 XP
    stars = xp_amount // 10

    await bot.send_invoice(
        chat_id=callback.from_user.id,
        title=f"{xp_amount} XP",
        description=(
            f"Покупка {xp_amount} XP "
            f"для StudyGo"
        ),
        payload=f"xp:{xp_amount}",
        currency="XTR",
        prices=[
            LabeledPrice(
                label=f"{xp_amount} XP",
                amount=stars
            )
        ]
    )

    await callback.answer()


# ============================================================
# PREMIUM PAYMENTS
# ============================================================

PREMIUM_PACKAGES = {
    "premium_1": {
        "days": 1,
        "stars": 50
    },
    "premium_7": {
        "days": 7,
        "stars": 200
    },
    "premium_30": {
        "days": 30,
        "stars": 750
    }
}


@dp.callback_query(F.data.startswith("premium_"))
async def premium_purchase_handler(
    callback: CallbackQuery
):

    key = callback.data

    package = PREMIUM_PACKAGES.get(
        key
    )

    if not package:
        await callback.answer(
            "❌ Неизвестный тариф.",
            show_alert=True
        )
        return

    days = package["days"]
    stars = package["stars"]

    await bot.send_invoice(
        chat_id=callback.from_user.id,
        title=f"StudyGo Premium — {days} дн.",
        description=(
            "Неограниченные AI-запросы "
            "и расширенные возможности StudyGo."
        ),
        payload=f"premium:{days}",
        currency="XTR",
        prices=[
            LabeledPrice(
                label=f"Premium {days} дней",
                amount=stars
            )
        ]
    )

    await callback.answer()


# ============================================================
# PRE-CHECKOUT
# ============================================================

@dp.pre_checkout_query()
async def pre_checkout_handler(
    query: PreCheckoutQuery
):

    await query.answer(
        ok=True
    )


# ============================================================
# SUCCESSFUL PAYMENT
# ============================================================

@dp.message(F.successful_payment)
async def successful_payment_handler(
    message: Message
):

    payment = message.successful_payment

    if not payment:
        return

    user_id = message.from_user.id
    payload = payment.invoice_payload
    telegram_payment_id = (
        payment.telegram_payment_charge_id
    )

    try:

        # XP
        if payload.startswith("xp:"):

            xp_amount = int(
                payload.split(":")[1]
            )

            add_xp(
                user_id,
                xp_amount,
                "stars_purchase",
                f"Покупка за {payment.total_amount} ⭐"
            )

            save_stars_transaction(
                user_id,
                payment.total_amount,
                "xp",
                str(xp_amount),
                telegram_payment_id
            )

            await message.answer(
                "✅ <b>Оплата прошла!</b>\n\n"
                f"⭐ Получено: <b>{xp_amount} XP</b>\n"
                f"💰 Потрачено: "
                f"<b>{payment.total_amount} ⭐</b>\n\n"
                f"Твой баланс: "
                f"<b>{get_xp(user_id)} XP</b>",
                parse_mode="HTML"
            )

        # Premium
        elif payload.startswith("premium:"):

            days = int(
                payload.split(":")[1]
            )

            expires = add_premium(
                user_id,
                days
            )

            save_premium_purchase(
                user_id,
                payment.total_amount,
                days,
                telegram_payment_id,
                expires
            )

            save_stars_transaction(
                user_id,
                payment.total_amount,
                "premium",
                str(days),
                telegram_payment_id
            )

            await message.answer(
                "💎 <b>PREMIUM АКТИВИРОВАН!</b>\n\n"
                f"Срок: <b>{days} дней</b>\n"
                f"До: <b>{expires.strftime('%d.%m.%Y %H:%M')}</b>\n\n"
                "♾️ Теперь AI-запросы "
                "не тратят XP.",
                parse_mode="HTML"
            )

    except Exception as e:

        logger.exception(
            "Ошибка обработки оплаты: %s",
            e
        )

        await message.answer(
            "⚠️ Оплата получена, "
            "но произошла ошибка обработки. "
            "Обратись к администратору."
        )


# ============================================================
# ADMIN PANEL
# ============================================================

def admin_keyboard():

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📊 Статистика",
                    callback_data="admin_stats"
                )
            ],
            [
                InlineKeyboardButton(
                    text="👥 Пользователи",
                    callback_data="admin_users"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📢 Рассылка",
                    callback_data="admin_broadcast"
                )
            ],
            [
                InlineKeyboardButton(
                    text="⭐ Выдать XP",
                    callback_data="admin_xp"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🚫 Заблокировать",
                    callback_data="admin_block"
                )
            ],
            [
                InlineKeyboardButton(
                    text="💎 Выдать Premium",
                    callback_data="admin_premium"
                )
            ]
        ]
    )


@dp.message(Command("admin"))
async def admin_handler(message: Message):

    if message.from_user.id != ADMIN_ID:
        await message.answer(
            "⛔ Доступ запрещён."
        )
        return

    await message.answer(
        "🛠 <b>ADMIN PANEL</b>\n\n"
        "Выбери действие:",
        reply_markup=admin_keyboard(),
        parse_mode="HTML"
    )


@dp.callback_query(F.data.startswith("admin_"))
async def admin_callback_handler(
    callback: CallbackQuery
):

    if callback.from_user.id != ADMIN_ID:
        await callback.answer(
            "⛔ Нет доступа.",
            show_alert=True
        )
        return

    action = callback.data

    if action == "admin_stats":

        users = get_total_users()
        premium = get_total_premium_users()
        total_xp = get_total_xp()

        await callback.message.edit_text(
            "📊 <b>СТАТИСТИКА</b>\n\n"
            f"👥 Пользователей: <b>{users}</b>\n"
            f"💎 Premium: <b>{premium}</b>\n"
            f"⭐ Всего XP: <b>{total_xp}</b>",
            reply_markup=admin_keyboard(),
            parse_mode="HTML"
        )

    elif action == "admin_users":

        users = get_total_users()

        await callback.message.edit_text(
            "👥 <b>ПОЛЬЗОВАТЕЛИ</b>\n\n"
            f"Всего пользователей: <b>{users}</b>",
            reply_markup=admin_keyboard(),
            parse_mode="HTML"
        )

    elif action == "admin_xp":

        user_modes[
            callback.from_user.id
        ] = "admin_xp"

        await callback.message.edit_text(
            "⭐ <b>ВЫДАТЬ XP</b>\n\n"
            "Отправь сообщение в формате:\n\n"
            "<code>ID КОЛИЧЕСТВО</code>\n\n"
            "Например:\n"
            "<code>123456789 500</code>",
            parse_mode="HTML"
        )

    elif action == "admin_premium":

        user_modes[
            callback.from_user.id
        ] = "admin_premium"

        await callback.message.edit_text(
            "💎 <b>ВЫДАТЬ PREMIUM</b>\n\n"
            "Отправь:\n"
            "<code>ID ДНИ</code>\n\n"
            "Например:\n"
            "<code>123456789 30</code>",
            parse_mode="HTML"
        )

    elif action == "admin_block":

        user_modes[
            callback.from_user.id
        ] = "admin_block"

        await callback.message.edit_text(
            "🚫 <b>БЛОКИРОВКА</b>\n\n"
            "Отправь ID пользователя.",
            parse_mode="HTML"
        )

    elif action == "admin_broadcast":

        user_modes[
            callback.from_user.id
        ] = "admin_broadcast"

        await callback.message.edit_text(
            "📢 <b>РАССЫЛКА</b>\n\n"
            "Отправь текст сообщения.",
            parse_mode="HTML"
        )

    await callback.answer()# ============================================================
# ADMIN TEXT COMMANDS
# ============================================================

@dp.message(F.text)
async def admin_text_processor(message: Message):

    if message.from_user.id != ADMIN_ID:
        return

    mode = user_modes.get(
        message.from_user.id
    )

    if not mode:
        return

    text = message.text.strip()

    try:

        if mode == "admin_xp":

            parts = text.split()

            if len(parts) != 2:
                raise ValueError

            target_id = int(parts[0])
            amount = int(parts[1])

            add_xp(
                target_id,
                amount,
                "admin",
                f"Выдано администратором {message.from_user.id}"
            )

            add_admin_log(
                message.from_user.id,
                "add_xp",
                target_id,
                amount
            )

            await message.answer(
                f"✅ Выдано <b>{amount} XP</b>\n"
                f"Пользователь: <code>{target_id}</code>",
                parse_mode="HTML"
            )

        elif mode == "admin_premium":

            parts = text.split()

            if len(parts) != 2:
                raise ValueError

            target_id = int(parts[0])
            days = int(parts[1])

            expires = add_premium(
                target_id,
                days
            )

            add_admin_log(
                message.from_user.id,
                "add_premium",
                target_id,
                days
            )

            await message.answer(
                "✅ Premium выдан.\n\n"
                f"ID: <code>{target_id}</code>\n"
                f"Дней: <b>{days}</b>\n"
                f"До: <b>{expires}</b>",
                parse_mode="HTML"
            )

        elif mode == "admin_block":

            target_id = int(text)

            set_blocked(
                target_id,
                True
            )

            add_admin_log(
                message.from_user.id,
                "block",
                target_id
            )

            await message.answer(
                f"🚫 Пользователь "
                f"<code>{target_id}</code> заблокирован.",
                parse_mode="HTML"
            )

        elif mode == "admin_broadcast":

            # Рассылка по всем пользователям.
            # Используем БД напрямую, чтобы не хранить
            # список пользователей в памяти.
            import psycopg2

            from database import DATABASE_URL

            conn = psycopg2.connect(
                DATABASE_URL
            )

            try:

                cur = conn.cursor()

                cur.execute(
                    "SELECT user_id FROM users "
                    "WHERE is_blocked = FALSE;"
                )

                users = cur.fetchall()

            finally:

                conn.close()

            sent = 0

            for row in users:

                target_id = row[0]

                try:

                    await bot.send_message(
                        target_id,
                        text
                    )

                    sent += 1

                    await asyncio.sleep(
                        0.05
                    )

                except Exception:
                    pass

            add_admin_log(
                message.from_user.id,
                "broadcast",
                amount=sent,
                details=text[:500]
            )

            await message.answer(
                f"📢 Рассылка завершена.\n\n"
                f"Отправлено: <b>{sent}</b>",
                parse_mode="HTML"
            )

        user_modes.pop(
            message.from_user.id,
            None
        )

    except (ValueError, TypeError):

        await message.answer(
            "❌ Неверный формат."
        )

    except Exception as e:

        logger.exception(
            "Admin error: %s",
            e
        )

        await message.answer(
            "❌ Ошибка выполнения."
        )


# ============================================================
# DAILY RANKING
# ============================================================

async def daily_reset():

    try:

        save_daily_rank()

        logger.info(
            "Ежедневный рейтинг обновлён."
        )

    except Exception as e:

        logger.exception(
            "Ошибка ежедневного рейтинга: %s",
            e
        )


# ============================================================
# STARTUP
# ============================================================

async def main():

    logger.info(
        "Запуск StudyGo..."
    )

    init_db()

    scheduler.add_job(
        daily_reset,
        "cron",
        hour=0,
        minute=0
    )

    scheduler.start()

    await bot.delete_webhook(
        drop_pending_updates=True
    )

    logger.info(
        "StudyGo запущен."
    )

    await dp.start_polling(
        bot
    )


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    flask_thread = threading.Thread(
        target=run_flask,
        daemon=True
    )

    flask_thread.start()

    try:

        asyncio.run(
            main()
        )

    except KeyboardInterrupt:

        logger.info(
            "StudyGo остановлен."
              )
)
