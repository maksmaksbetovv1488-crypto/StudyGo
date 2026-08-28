"""Admin panel."""

import asyncio

from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext

from config import ADMIN_ID
from keyboards import admin_kb, back_kb, main_menu_kb
from states import AdminStates
from handlers.start import safe_edit
from database import (
    get_users_stats,
    get_stars_stats,
    get_ai_stats,
    get_referral_stats,
    get_top_referrers,
    get_admin_logs,
    search_user,
    get_referral_count,
    change_xp,
    add_premium_days,
    set_blocked,
    get_user,
    get_all_user_ids,
)

router = Router()


def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID and ADMIN_ID != 0


@router.message(Command("admin"))
async def cmd_admin(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Доступ запрещён.")
        return
    await message.answer("⚙️ <b>Admin Panel</b>", reply_markup=admin_kb())


@router.callback_query(F.data == "adm_users")
async def adm_users(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    s = get_users_stats()
    text = (
        f"👥 <b>Пользователи</b>\n\n"
        f"Всего: {s['total']}\n"
        f"Новых сегодня: {s['new_today']}\n"
        f"Новых за неделю: {s['new_week']}\n"
        f"Активных сегодня: {s['active_today']}\n"
        f"Активных за неделю: {s['active_week']}\n"
        f"Premium: {s['premium']}\n"
        f"Заблокированных: {s['blocked']}"
    )
    await safe_edit(callback.message, text, reply_markup=admin_kb())
    await callback.answer()


@router.callback_query(F.data == "adm_stars")
async def adm_stars(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    t = get_stars_stats("today")
    w = get_stars_stats("week")
    m = get_stars_stats("month")
    a = get_stars_stats("all")
    text = (
        f"⭐ <b>Stars</b>\n\n"
        f"Сегодня: {t['total_stars']} ⭐\n"
        f"Неделя: {w['total_stars']} ⭐\n"
        f"Месяц: {m['total_stars']} ⭐\n"
        f"Всё время: {a['total_stars']} ⭐\n\n"
        f"Покупок XP: {a['xp_purchases']}\n"
        f"Premium: {a['premium_purchases']}"
    )
    await safe_edit(callback.message, text, reply_markup=admin_kb())
    await callback.answer()


@router.callback_query(F.data == "adm_stats")
async def adm_stats(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    ai = get_ai_stats("today")
    text = (
        f"📊 <b>Статистика сегодня</b>\n\n"
        f"AI-запросы: {ai['total']}\n"
        f"Фото: {ai['photo']}\n"
        f"Premium-запросы: {ai['premium_requests']}\n"
        f"XP потрачено: {ai['xp_spent']}"
    )
    await safe_edit(callback.message, text, reply_markup=admin_kb())
    await callback.answer()


@router.callback_query(F.data == "adm_refs")
async def adm_refs(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    s = get_referral_stats()
    top = get_top_referrers(5)
    lines = [
        f"🎁 <b>Рефералы</b>\n",
        f"Всего: {s['total']}",
        f"Подтверждённых: {s['confirmed']}",
        f"Сегодня: {s['today']}\n",
        "Топ рефереров:",
    ]
    for t in top:
        name = t.get("username") or t.get("first_name") or t["referrer_id"]
        lines.append(f"• {name}: {t['cnt']}")
    await safe_edit(callback.message, "\n".join(lines), reply_markup=admin_kb())
    await callback.answer()


@router.callback_query(F.data == "adm_logs")
async def adm_logs(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    logs = get_admin_logs(20)
    if not logs:
        text = "📋 Логов пока нет."
    else:
        lines = ["📋 <b>Последние логи</b>\n"]
        for l in logs:
            lines.append(
                f"{l['created_at']:%d.%m %H:%M} | "
                f"A:{l['admin_id']} → {l['action']} "
                f"U:{l['target_id']} amt:{l['amount']}"
            )
        text = "\n".join(lines)
    await safe_edit(callback.message, text, reply_markup=admin_kb())
    await callback.answer()


@router.callback_query(F.data == "adm_search")
async def adm_search(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    await state.set_state(AdminStates.search_user)
    await safe_edit(
        callback.message,
        "🔍 Введите Telegram ID или username:",
        reply_markup=back_kb("main"),
    )
    await callback.answer()


@router.message(AdminStates.search_user)
async def process_admin_search(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    user = search_user(message.text.strip())
    await state.clear()
    if not user:
        await message.answer("Не найден.", reply_markup=admin_kb())
        return
    refs = get_referral_count(user["user_id"])
    text = (
        f"ID: <code>{user['user_id']}</code>\n"
        f"Username: @{user['username'] or '—'}\n"
        f"XP: {user['xp']}\n"
        f"Score: {user['score']}\n"
        f"Daily Score: {user['daily_score']}\n"
        f"Level: {user['level']}\n"
        f"Premium: {user.get('premium_until') or '—'}\n"
        f"Рефералы: {refs}\n"
        f"Blocked: {user['is_blocked']}\n"
        f"Регистрация: {user['created_at']}"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="➕ XP", callback_data=f"adm_xp_plus:{user['user_id']}"),
            InlineKeyboardButton(text="➖ XP", callback_data=f"adm_xp_minus:{user['user_id']}"),
        ],
        [
            InlineKeyboardButton(text="💎 +7д Premium", callback_data=f"adm_prem:{user['user_id']}:7"),
            InlineKeyboardButton(
                text="🚫 BAN" if not user["is_blocked"] else "🔓 UNBAN",
                callback_data=f"adm_ban:{user['user_id']}",
            ),
        ],
        [InlineKeyboardButton(text="◀️ Админка", callback_data="adm_users")],
    ])
    await message.answer(text, reply_markup=kb)


@router.callback_query(F.data.startswith("adm_xp_plus:"))
async def adm_xp_plus(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    uid = int(callback.data.split(":")[1])
    change_xp(uid, 100, "admin", "Admin +100", admin_id=callback.from_user.id)
    await callback.answer("+100 XP выдано", show_alert=True)


@router.callback_query(F.data.startswith("adm_xp_minus:"))
async def adm_xp_minus(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    uid = int(callback.data.split(":")[1])
    try:
        change_xp(uid, -100, "admin", "Admin -100", admin_id=callback.from_user.id)
        await callback.answer("-100 XP", show_alert=True)
    except ValueError:
        await callback.answer("Недостаточно XP у пользователя", show_alert=True)


@router.callback_query(F.data.startswith("adm_prem:"))
async def adm_prem(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    parts = callback.data.split(":")
    uid, days = int(parts[1]), int(parts[2])
    add_premium_days(uid, days, admin_id=callback.from_user.id)
    await callback.answer(f"Premium +{days} дней", show_alert=True)


@router.callback_query(F.data.startswith("adm_ban:"))
async def adm_ban(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    uid = int(callback.data.split(":")[1])
    user = get_user(uid)
    new_state = not user["is_blocked"]
    set_blocked(uid, new_state, admin_id=callback.from_user.id)
    await callback.answer("BAN" if new_state else "UNBAN", show_alert=True)


@router.callback_query(F.data == "adm_broadcast")
async def adm_broadcast(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    await state.set_state(AdminStates.broadcast_text)
    await safe_edit(
        callback.message,
        "📢 Введите текст рассылки (HTML):",
        reply_markup=back_kb("main"),
    )
    await callback.answer()


@router.message(AdminStates.broadcast_text)
async def process_broadcast(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.update_data(broadcast_text=message.html_text or message.text)
    ids = get_all_user_ids()
    await state.set_state(AdminStates.broadcast_confirm)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Отправить", callback_data="bc_yes"),
            InlineKeyboardButton(text="❌ Отмена", callback_data="main"),
        ]
    ])
    await message.answer(
        f"⚠️ Подтвердить рассылку?\n\nПолучателей: <b>{len(ids)}</b>\n\n"
        f"{message.html_text or message.text}",
        reply_markup=kb,
    )


@router.callback_query(F.data == "bc_yes")
async def bc_yes(callback: CallbackQuery, state: FSMContext, bot: Bot):
    if not is_admin(callback.from_user.id):
        return
    data = await state.get_data()
    text = data.get("broadcast_text", "")
    await state.clear()
    ids = get_all_user_ids()
    ok, fail = 0, 0
    await callback.message.edit_text(f"Рассылка... 0/{len(ids)}")
    for i, uid in enumerate(ids):
        try:
            await bot.send_message(uid, text)
            ok += 1
        except Exception:
            fail += 1
        if i % 20 == 0:
            await asyncio.sleep(1)
    await callback.message.edit_text(
        f"✅ Рассылка завершена.\nУспешно: {ok}\nОшибок: {fail}",
        reply_markup=admin_kb(),
    )
    await callback.answer()
