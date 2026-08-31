"""Бонусы, профиль, пересылки чатов."""

import logging
from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, Message

from keyboards import back_kb, earn_kb, earn_chats_kb
from handlers.start import safe_edit
from plans import BIO_TAG, BIO_BONUS, CHAT_BONUS_PER, CHAT_BONUS_MAX, CHATS_NEED_MEMBERS, plan_title
from database import (
    get_user, get_active_plan, get_used_today, get_daily_limit, chats_bonus,
    count_user_chats, get_referral_count, register_forward_chat,
)

logger = logging.getLogger("studygo.social")
router = Router()


async def check_bio(bot: Bot, user_id: int) -> bool:
    try:
        chat = await bot.get_chat(user_id)
        bio = (getattr(chat, "bio", None) or "") + " "
        about = getattr(chat, "description", None) or ""
        return BIO_TAG.lower() in (bio + about).lower()
    except Exception:
        return False


def _extract_forward_source(message: Message):
    if message.forward_from_chat:
        c = message.forward_from_chat
        return c.id, getattr(c, "type", None), getattr(c, "title", None)
    if message.forward_from:
        u = message.forward_from
        return u.id, "private", u.full_name
    origin = getattr(message, "forward_origin", None)
    if origin is None:
        return None, None, None
    otype = type(origin).__name__
    if otype == "MessageOriginChannel":
        ch = origin.chat
        return ch.id, "channel", getattr(ch, "title", None)
    if otype == "MessageOriginChat":
        ch = origin.sender_chat
        return ch.id, getattr(ch, "type", "group"), getattr(ch, "title", None)
    if otype == "MessageOriginUser":
        u = origin.sender_user
        return u.id, "private", u.full_name
    if otype == "MessageOriginHiddenUser":
        name = getattr(origin, "sender_user_name", "hidden") or "hidden"
        return hash(name) % (10**12), "hidden", name
    return None, None, None


@router.message(F.forward_origin | F.forward_from_chat | F.forward_from)
async def on_forward(message: Message, bot: Bot):
    user = message.from_user
    if not user:
        return
    chat_id, ctype, title = _extract_forward_source(message)
    if not chat_id:
        await message.answer("Не удалось определить чат.")
        return

    members = None
    # попытка узнать число участников (если бот в чате)
    try:
        if ctype not in ("private", "hidden"):
            members = await bot.get_chat_member_count(chat_id)
    except Exception:
        members = None

    if members is not None and members <= CHATS_NEED_MEMBERS:
        await message.answer(
            f"Чат «{title or chat_id}»: {members} чел. Нужно больше {CHATS_NEED_MEMBERS}."
        )
        return

    if members is None and ctype == "private":
        await message.answer("Личные чаты не считаются. Нужна группа/канал > 5 человек.")
        return

    # если members неизвестен — всё равно засчитываем с пометкой (юзер мог переслать)
    # строже: без members не считать, кроме случая когда API недоступен
    if members is None:
        await message.answer(
            "Не могу проверить число участников (бот не в этом чате).\n"
            "Добавь бота в группу/канал с >5 людьми и перешли снова, "
            "либо перешли из чата, где бот уже есть."
        )
        return

    register_forward_chat(user.id, chat_id, ctype, title, members)
    n = count_user_chats(user.id)
    bonus = min(CHAT_BONUS_MAX, n * CHAT_BONUS_PER)
    await message.answer(
        f"✅ Чат засчитан ({members} чел.)\n"
        f"Всего чатов: <b>{n}</b> → бонус к лимиту <b>+{bonus}</b> (макс +{CHAT_BONUS_MAX})"
    )


@router.callback_query(F.data == "earn")
async def cb_earn(callback: CallbackQuery):
    text = (
        "🎁 <b>Бонусы</b>\n\n"
        "👥 Рефералы — +3 дня Free+ тебе\n"
        f"💜 Приписка @{BIO_TAG} — +{BIO_BONUS} к лимиту/день\n"
        f"💬 Чаты (>5 чел.) — +{CHAT_BONUS_PER} за чат, макс +{CHAT_BONUS_MAX}"
    )
    await safe_edit(callback.message, text, reply_markup=earn_kb())
    await callback.answer()


@router.callback_query(F.data == "earn_refs")
async def cb_refs(callback: CallbackQuery, bot: Bot):
    uid = callback.from_user.id
    count = get_referral_count(uid)
    me = await bot.get_me()
    link = f"https://t.me/{me.username}?start=ref_{uid}"
    await safe_edit(
        callback.message,
        f"👥 <b>Рефералы</b>\n\n"
        f"Успешных: <b>{count}</b>\n\n"
        f"Ссылка:\n<code>{link}</code>\n\n"
        f"Друг: ссылка → подписка на канал → «Я подписался».\n"
        f"Тебе: <b>+3 дня Free+</b>. Другу — ничего.",
        reply_markup=back_kb("earn"),
    )
    await callback.answer()


@router.callback_query(F.data == "earn_bio")
async def cb_bio(callback: CallbackQuery, bot: Bot):
    has = await check_bio(bot, callback.from_user.id)
    await safe_edit(
        callback.message,
        f"💜 <b>Приписка</b>\n\n"
        f"Добавь в описание профиля:\n<code>@{BIO_TAG}</code>\n\n"
        f"Пока приписка есть: <b>+{BIO_BONUS}</b> запросов к дневному лимиту.\n\n"
        f"Сейчас: <b>{'есть ✅' if has else 'нет ❌'}</b>",
        reply_markup=back_kb("earn"),
    )
    await callback.answer()


@router.callback_query(F.data == "earn_chats")
async def cb_chats(callback: CallbackQuery):
    n = count_user_chats(callback.from_user.id)
    bonus = chats_bonus(callback.from_user.id)
    await safe_edit(
        callback.message,
        f"💬 <b>Чаты</b>\n\n"
        f"Перешли боту сообщение из группы/канала, где:\n"
        f"• больше {CHATS_NEED_MEMBERS} человек\n"
        f"• бот может проверить число участников (лучше добавить бота в чат)\n\n"
        f"За каждый чат: <b>+{CHAT_BONUS_PER}</b> к лимиту навсегда "
        f"(макс +{CHAT_BONUS_MAX}).\n\n"
        f"Сейчас: <b>{n}</b> чатов → <b>+{bonus}</b> к лимиту.",
        reply_markup=earn_chats_kb(),
    )
    await callback.answer()


@router.callback_query(F.data == "profile")
async def cb_profile(callback: CallbackQuery, bot: Bot):
    uid = callback.from_user.id
    user = get_user(uid)
    if not user:
        await callback.answer("Не найден", show_alert=True)
        return
    plan = get_active_plan(uid)
    has_bio = await check_bio(bot, uid)
    used = get_used_today(uid)
    limit = get_daily_limit(uid, has_bio=has_bio)
    until = user.get("plan_until")
    until_s = until.strftime("%d.%m.%Y %H:%M") if until else "—"
    refs = get_referral_count(uid)
    nch = count_user_chats(uid)
    text = (
        f"👤 <b>Профиль</b>\n\n"
        f"ID: <code>{uid}</code>\n"
        f"@{user.get('username') or '—'}\n"
        f"💎 Тариф: <b>{plan_title(plan)}</b>\n"
        f"До: {until_s}\n"
        f"📊 Сегодня: <b>{used}/{limit}</b>\n"
        f"💜 Приписка: {'да' if has_bio else 'нет'}\n"
        f"💬 Чатов: {nch} (+{chats_bonus(uid)})\n"
        f"👥 Рефералы: {refs}"
    )
    await safe_edit(callback.message, text, reply_markup=back_kb())
    await callback.answer()
