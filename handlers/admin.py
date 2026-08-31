"""Admin panel."""

import asyncio
from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext

from config import ADMIN_IDS
from keyboards import admin_kb, back_kb
from states import AdminStates
from handlers.start import safe_edit
from plans import PLANS, PLAN_ORDER, plan_title
from database import (
    get_users_stats, get_stars_stats, get_ai_stats, get_referral_stats,
    get_top_referrers, get_admin_logs, search_user, get_referral_count,
    add_plan_days, set_plan_free, set_blocked, get_user, get_all_user_ids,
    get_active_plan, admin_reset_limit, get_used_today, get_daily_limit,
)

router = Router()


def is_admin(uid: int) -> bool:
    return uid in ADMIN_IDS


@router.message(Command("admin"))
async def cmd_admin(message: Message):
    uid = message.from_user.id
    if not is_admin(uid):
        await message.answer(
            f"⛔ Нет доступа.\nВаш ID: <code>{uid}</code>\n"
            f"Добавьте в ADMIN_ID на Render."
        )
        return
    await message.answer("⚙️ <b>Admin Panel</b>", reply_markup=admin_kb())


@router.callback_query(F.data == "adm_users")
async def adm_users(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    s = get_users_stats()
    await safe_edit(
        callback.message,
        f"👥 <b>Юзеры</b>\n\n"
        f"Всего: {s['total']}\n"
        f"Сегодня: {s['new_today']}\n"
        f"Неделя: {s['new_week']}\n"
        f"Платных: {s['paid']}\n"
        f"Бан: {s['blocked']}",
        reply_markup=admin_kb(),
    )
    await callback.answer()


@router.callback_query(F.data == "adm_stars")
async def adm_stars(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    t, w, a = get_stars_stats("today"), get_stars_stats("week"), get_stars_stats("all")
    await safe_edit(
        callback.message,
        f"⭐ <b>Stars</b>\n\n"
        f"Сегодня: {t['total_stars']} ⭐ ({t['purchases']} покупок)\n"
        f"Неделя: {w['total_stars']} ⭐\n"
        f"Всё время: {a['total_stars']} ⭐",
        reply_markup=admin_kb(),
    )
    await callback.answer()


@router.callback_query(F.data == "adm_stats")
async def adm_stats(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    ai = get_ai_stats("today")
    await safe_edit(
        callback.message,
        f"📊 <b>AI сегодня</b>\n\nЗапросов: {ai['total']}\nФото: {ai['photo']}",
        reply_markup=admin_kb(),
    )
    await callback.answer()


@router.callback_query(F.data == "adm_refs")
async def adm_refs(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    s = get_referral_stats()
    top = get_top_referrers(5)
    lines = [f"🎁 Рефы: всего {s['total']}, подтв. {s['confirmed']}, сегодня {s['today']}\n"]
    for t in top:
        name = t.get("username") or t.get("first_name") or t["referrer_id"]
        lines.append(f"• {name}: {t['cnt']}")
    await safe_edit(callback.message, "\n".join(lines), reply_markup=admin_kb())
    await callback.answer()


@router.callback_query(F.data == "adm_logs")
async def adm_logs(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    logs = get_admin_logs(15)
    if not logs:
        text = "Логов нет."
    else:
        lines = ["📋 <b>Логи</b>\n"]
        for l in logs:
            lines.append(f"{l['created_at']:%d.%m %H:%M} {l['action']} → {l['target_id']} {l.get('details') or ''}")
        text = "\n".join(lines)
    await safe_edit(callback.message, text, reply_markup=admin_kb())
    await callback.answer()


@router.callback_query(F.data == "adm_search")
async def adm_search(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    await state.set_state(AdminStates.search_user)
    await safe_edit(callback.message, "🔍 ID или username:", reply_markup=back_kb("main"))
    await callback.answer()


@router.message(AdminStates.search_user)
async def process_search(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    user = search_user(message.text.strip())
    await state.clear()
    if not user:
        await message.answer("Не найден.", reply_markup=admin_kb())
        return
    uid = user["user_id"]
    plan = get_active_plan(uid)
    used = get_used_today(uid)
    limit = get_daily_limit(uid)
    refs = get_referral_count(uid)
    until = user.get("plan_until")
    until_s = until.strftime("%d.%m.%Y") if until else "—"
    text = (
        f"ID: <code>{uid}</code>\n"
        f"@{user.get('username') or '—'}\n"
        f"План: {plan_title(plan)} до {until_s}\n"
        f"Лимит: {used}/{limit}\n"
        f"Рефы: {refs}\n"
        f"Бан: {user['is_blocked']}"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Free+", callback_data=f"adm_plan:{uid}:free_plus"),
            InlineKeyboardButton(text="Pro", callback_data=f"adm_plan:{uid}:pro"),
        ],
        [
            InlineKeyboardButton(text="Pro+", callback_data=f"adm_plan:{uid}:pro_plus"),
            InlineKeyboardButton(text="Ultra", callback_data=f"adm_plan:{uid}:ultra"),
        ],
        [
            InlineKeyboardButton(text="Снять → Free", callback_data=f"adm_plan_free:{uid}"),
            InlineKeyboardButton(text="Сброс лимита", callback_data=f"adm_reset:{uid}"),
        ],
        [
            InlineKeyboardButton(
                text="BAN" if not user["is_blocked"] else "UNBAN",
                callback_data=f"adm_ban:{uid}",
            ),
        ],
        [InlineKeyboardButton(text="◀️ Админка", callback_data="adm_users")],
    ])
    await message.answer(text, reply_markup=kb)


@router.callback_query(F.data.startswith("adm_plan:"))
async def adm_plan(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    _, uid_s, plan_id = callback.data.split(":")
    await state.update_data(adm_target=int(uid_s), adm_plan=plan_id)
    await state.set_state(AdminStates.give_days)
    await callback.message.answer(f"Сколько дней {plan_title(plan_id)}? (число)")
    await callback.answer()


@router.message(AdminStates.give_days)
async def process_days(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    data = await state.get_data()
    await state.clear()
    try:
        days = int(message.text.strip())
    except ValueError:
        await message.answer("Нужно число.", reply_markup=admin_kb())
        return
    uid = data["adm_target"]
    plan_id = data["adm_plan"]
    add_plan_days(uid, plan_id, days, admin_id=message.from_user.id)
    await message.answer(
        f"✅ {plan_title(plan_id)} на {days} дн. → <code>{uid}</code>",
        reply_markup=admin_kb(),
    )


@router.callback_query(F.data.startswith("adm_plan_free:"))
async def adm_plan_free(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    uid = int(callback.data.split(":")[1])
    set_plan_free(uid, admin_id=callback.from_user.id)
    await callback.answer("Сброшено на Free", show_alert=True)


@router.callback_query(F.data.startswith("adm_reset:"))
async def adm_reset(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    uid = int(callback.data.split(":")[1])
    admin_reset_limit(uid, admin_id=callback.from_user.id)
    await callback.answer("Лимит сброшен", show_alert=True)


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
    await safe_edit(callback.message, "📢 Текст рассылки (HTML):", reply_markup=back_kb("main"))
    await callback.answer()


@router.message(AdminStates.broadcast_text)
async def process_bc(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.update_data(broadcast_text=message.html_text or message.text)
    ids = get_all_user_ids()
    await state.set_state(AdminStates.broadcast_confirm)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Отправить", callback_data="bc_yes"),
            InlineKeyboardButton(text="❌", callback_data="main"),
        ]
    ])
    await message.answer(f"Получателей: {len(ids)}\n\n{message.html_text or message.text}", reply_markup=kb)


@router.callback_query(F.data == "bc_yes")
async def bc_yes(callback: CallbackQuery, state: FSMContext, bot: Bot):
    if not is_admin(callback.from_user.id):
        return
    data = await state.get_data()
    text = data.get("broadcast_text", "")
    await state.clear()
    ids = get_all_user_ids()
    ok = fail = 0
    await callback.message.edit_text(f"Рассылка 0/{len(ids)}")
    for i, uid in enumerate(ids):
        try:
            await bot.send_message(uid, text)
            ok += 1
        except Exception:
            fail += 1
        if i % 20 == 0:
            await asyncio.sleep(1)
    await callback.message.edit_text(f"✅ Готово. Ок: {ok}, ошибок: {fail}", reply_markup=admin_kb())
    await callback.answer()
