"""Rank, referrals, tasks, profile."""

from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery

from keyboards import main_menu_kb, back_kb, rank_kb, tasks_kb
from handlers.start import safe_edit
from database import (
    get_user,
    is_premium,
    get_user_daily_place,
    get_referral_count,
    get_user_achievements,
    get_daily_rank,
    get_rank_history,
    get_setting_int,
    get_streak,
    mark_daily_completed,
    claim_daily_reward,
)

router = Router()


def format_user_profile(user: dict) -> str:
    prem = "активен" if is_premium(user["user_id"]) else "нет"
    place = get_user_daily_place(user["user_id"])
    place_str = f"#{place}" if place else "—"
    refs = get_referral_count(user["user_id"])
    achs = get_user_achievements(user["user_id"])
    ach_str = ", ".join(a["icon"] + " " + a["title"] for a in achs) if achs else "пока нет"
    return (
        f"👤 <b>Профиль</b>\n\n"
        f"ID: <code>{user['user_id']}</code>\n"
        f"Username: @{user['username'] or '—'}\n"
        f"🟣 XP: <b>{user['xp']:,}</b>\n"
        f"🏆 Score: <b>{user['score']:,}</b>\n"
        f"🎖️ Level: <b>{user['level']}</b>\n"
        f"⚡ Daily Rank: {place_str}\n"
        f"🔥 Streak: {user['streak']} дн.\n"
        f"📝 Решённые задания: {user['solved_tasks']}\n"
        f"👥 Рефералы: {refs}\n"
        f"💎 Premium: {prem}\n"
        f"🏅 Достижения: {ach_str}"
    )


@router.callback_query(F.data == "rank")
async def cb_rank(callback: CallbackQuery):
    top = get_daily_rank(30)
    lines = ["🏆 <b>Daily Rank — TOP-30</b>\n"]
    medals = {1: "🥇", 2: "🥈", 3: "🥉"}
    for i, u in enumerate(top, 1):
        medal = medals.get(i, f"{i}.")
        name = u.get("username") or u.get("first_name") or str(u["user_id"])
        lines.append(f"{medal} {name} — {u['daily_score']} DS")
    my_place = get_user_daily_place(callback.from_user.id)
    if my_place:
        lines.append(f"\nВаше место: <b>#{my_place}</b>")
    text = "\n".join(lines) if top else "🏆 Рейтинг пока пуст."
    await safe_edit(callback.message, text, reply_markup=rank_kb())
    await callback.answer()


@router.callback_query(F.data == "rank_history")
async def cb_rank_history(callback: CallbackQuery):
    hist = get_rank_history(callback.from_user.id)
    if not hist:
        text = "📜 История пока пуста."
    else:
        lines = ["📜 <b>История Daily Rank</b>\n"]
        for h in hist:
            lines.append(
                f"{h['rank_date']}: место #{h['place']} "
                f"({h['daily_score']} DS) +{h['reward_xp']} XP"
            )
        text = "\n".join(lines)
    await safe_edit(callback.message, text, reply_markup=back_kb("rank"))
    await callback.answer()


@router.callback_query(F.data == "referrals")
async def cb_referrals(callback: CallbackQuery, bot: Bot):
    user_id = callback.from_user.id
    count = get_referral_count(user_id)
    me = await bot.get_me()
    link = f"https://t.me/{me.username}?start=ref_{user_id}"
    await safe_edit(
        callback.message,
        f"👥 <b>Рефералы</b>\n\n"
        f"Успешных: <b>{count}</b>\n\n"
        f"Ваша ссылка:\n<code>{link}</code>\n\n"
        f"Друг должен:\n"
        f"1. Перейти по ссылке\n"
        f"2. Подписаться на канал\n"
        f"3. Нажать «Я подписался»\n\n"
        f"Вы получите +{get_setting_int('referral_referrer_xp', 100)} XP\n"
        f"Друг получит +{get_setting_int('referral_referred_xp', 20)} XP",
        reply_markup=back_kb(),
    )
    await callback.answer()


@router.callback_query(F.data == "tasks")
async def cb_tasks(callback: CallbackQuery):
    user_id = callback.from_user.id
    streak = get_streak(user_id)
    await safe_edit(
        callback.message,
        f"🎯 <b>Задания</b>\n\n"
        f"🔥 Streak: <b>{streak}</b> дн.\n\n"
        f"Ежедневное задание: +{get_setting_int('daily_task_reward', 30)} XP\n"
        f"Серии: 3д +50 / 7д +100 / 30д +500 XP\n\n"
        f"Нажмите кнопку, чтобы отметить выполнение.",
        reply_markup=tasks_kb(),
    )
    await callback.answer()


@router.callback_query(F.data == "do_daily")
async def cb_do_daily(callback: CallbackQuery):
    user_id = callback.from_user.id
    mark_daily_completed(user_id)
    reward = claim_daily_reward(user_id)
    if reward is None:
        await callback.answer("Уже выполнено сегодня или награда получена.", show_alert=True)
        return
    await callback.answer(f"+{reward} XP!", show_alert=True)
    await cb_tasks(callback)


@router.callback_query(F.data == "profile")
async def cb_profile(callback: CallbackQuery):
    user = get_user(callback.from_user.id)
    if not user:
        await callback.answer("Пользователь не найден", show_alert=True)
        return
    text = format_user_profile(user)
    await safe_edit(callback.message, text, reply_markup=back_kb())
    await callback.answer()
