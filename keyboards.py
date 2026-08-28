"""StudyGo — inline keyboards."""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from config import CHANNEL_ID


def main_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🧠 AI-помощник", callback_data="ai_helper"),
            InlineKeyboardButton(text="📸 Решить по фото", callback_data="ai_photo"),
        ],
        [
            InlineKeyboardButton(text="📚 Объяснить тему", callback_data="ai_explain"),
            InlineKeyboardButton(text="📝 Создать тест", callback_data="ai_test"),
        ],
        [
            InlineKeyboardButton(text="✅ Проверить ответ", callback_data="ai_check"),
            InlineKeyboardButton(text="🟣 Мой XP", callback_data="my_xp"),
        ],
        [
            InlineKeyboardButton(text="💎 Premium", callback_data="premium"),
            InlineKeyboardButton(text="🏆 Рейтинг", callback_data="rank"),
        ],
        [
            InlineKeyboardButton(text="👥 Рефералы", callback_data="referrals"),
            InlineKeyboardButton(text="🎯 Задания", callback_data="tasks"),
        ],
        [InlineKeyboardButton(text="👤 Профиль", callback_data="profile")],
    ])


def back_kb(to: str = "main") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад", callback_data=to)]
    ])


def xp_packages_kb() -> InlineKeyboardMarkup:
    packages = [
        (1, 10), (5, 50), (10, 100), (25, 250),
        (50, 500), (100, 1000), (250, 2500), (500, 5000), (1000, 10000),
    ]
    rows, row = [], []
    for stars, xp in packages:
        row.append(InlineKeyboardButton(
            text=f"⭐{stars} → {xp} XP",
            callback_data=f"buy_xp:{stars}:{xp}",
        ))
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([InlineKeyboardButton(text="◀️ Назад", callback_data="my_xp")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def premium_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="1 день — ⭐50", callback_data="buy_prem:1:50")],
        [InlineKeyboardButton(text="7 дней — ⭐200", callback_data="buy_prem:7:200")],
        [InlineKeyboardButton(text="30 дней — ⭐750", callback_data="buy_prem:30:750")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="main")],
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
            InlineKeyboardButton(text="👥 Пользователи", callback_data="adm_users"),
            InlineKeyboardButton(text="🔍 Найти", callback_data="adm_search"),
        ],
        [
            InlineKeyboardButton(text="⭐ Stars", callback_data="adm_stars"),
            InlineKeyboardButton(text="📊 Статистика", callback_data="adm_stats"),
        ],
        [
            InlineKeyboardButton(text="🎁 Рефералы", callback_data="adm_refs"),
            InlineKeyboardButton(text="📋 Логи", callback_data="adm_logs"),
        ],
        [InlineKeyboardButton(text="📢 Рассылка", callback_data="adm_broadcast")],
        [InlineKeyboardButton(text="◀️ Закрыть", callback_data="main")],
    ])


def rank_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📜 История", callback_data="rank_history")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="main")],
    ])


def tasks_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Выполнить ежедневное", callback_data="do_daily")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="main")],
    ])
