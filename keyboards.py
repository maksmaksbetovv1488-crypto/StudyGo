"""StudyGo — keyboards."""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import CHANNEL_ID
from plans import PLANS, PLAN_ORDER


def main_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🧠 AI-помощник", callback_data="ai_helper"),
            InlineKeyboardButton(text="📸 По фото", callback_data="ai_photo"),
        ],
        [
            InlineKeyboardButton(text="📚 Тема", callback_data="ai_explain"),
            InlineKeyboardButton(text="📝 Тест", callback_data="ai_test"),
        ],
        [
            InlineKeyboardButton(text="✅ Проверить", callback_data="ai_check"),
            InlineKeyboardButton(text="📖 Конспект", callback_data="ai_conspect"),
        ],
        [
            InlineKeyboardButton(text="🔎 Разбор ошибки", callback_data="ai_error"),
            InlineKeyboardButton(text="📅 План недели", callback_data="ai_week"),
        ],
        [
            InlineKeyboardButton(text="💎 Подписка", callback_data="subscription"),
            InlineKeyboardButton(text="🎁 Бонусы", callback_data="earn"),
        ],
        [InlineKeyboardButton(text="👤 Профиль", callback_data="profile")],
    ])


def back_kb(to: str = "main") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад", callback_data=to)]
    ])


def subscription_kb() -> InlineKeyboardMarkup:
    rows = []
    for pid in PLAN_ORDER:
        p = PLANS[pid]
        if p["stars"] <= 0:
            continue
        rows.append([InlineKeyboardButton(
            text=f"{p['title']} — {p['stars']}⭐ / 30 дн.",
            callback_data=f"buy_plan:{pid}",
        )])
    rows.append([InlineKeyboardButton(text="◀️ Назад", callback_data="main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def earn_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👥 Рефералы", callback_data="earn_refs")],
        [InlineKeyboardButton(text="💜 Приписка", callback_data="earn_bio")],
        [InlineKeyboardButton(text="💬 Чаты", callback_data="earn_chats")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="main")],
    ])


def earn_chats_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад", callback_data="earn")],
    ])


def subscribe_kb() -> InlineKeyboardMarkup:
    channel = CHANNEL_ID.lstrip("@") if CHANNEL_ID else "channel"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Подписаться на канал", url=f"https://t.me/{channel}")],
        [InlineKeyboardButton(text="✅ Я подписался", callback_data="check_sub")],
    ])


def admin_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="👥 Юзеры", callback_data="adm_users"),
            InlineKeyboardButton(text="🔍 Найти", callback_data="adm_search"),
        ],
        [
            InlineKeyboardButton(text="⭐ Stars", callback_data="adm_stars"),
            InlineKeyboardButton(text="📊 AI", callback_data="adm_stats"),
        ],
        [
            InlineKeyboardButton(text="🎁 Рефы", callback_data="adm_refs"),
            InlineKeyboardButton(text="📋 Логи", callback_data="adm_logs"),
        ],
        [InlineKeyboardButton(text="📢 Рассылка", callback_data="adm_broadcast")],
        [InlineKeyboardButton(text="◀️ Закрыть", callback_data="main")],
    ])
