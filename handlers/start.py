"""Start, subscription, main menu."""

import logging

from aiogram import Router, F, Bot
from aiogram.enums import ChatMemberStatus
from aiogram.filters import CommandStart, CommandObject
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from config import CHANNEL_ID
from keyboards import main_menu_kb, subscribe_kb
from database import (
    ensure_user,
    is_blocked,
    create_referral,
    confirm_referral,
    get_pending_referral,
    grant_achievement,
)

logger = logging.getLogger("studygo.start")
router = Router()


async def check_channel_subscription(bot: Bot, user_id: int) -> bool:
    if not CHANNEL_ID:
        return True
    try:
        member = await bot.get_chat_member(CHANNEL_ID, user_id)
        return member.status in (
            ChatMemberStatus.MEMBER,
            ChatMemberStatus.ADMINISTRATOR,
            ChatMemberStatus.CREATOR,
        )
    except Exception as e:
        logger.warning("Subscription check failed: %s", e)
        return False


async def safe_edit(message: Message, text: str, reply_markup=None):
    try:
        await message.edit_text(text, reply_markup=reply_markup)
    except Exception:
        await message.answer(text, reply_markup=reply_markup)


@router.message(CommandStart())
async def cmd_start(message: Message, command: CommandObject):
    user = message.from_user
    if is_blocked(user.id):
        await message.answer("🚫 Вы заблокированы.")
        return

    ensure_user(user.id, user.username, user.first_name, user.last_name)

    # /start ref_123456
    if command.args and command.args.startswith("ref_"):
        try:
            referrer_id = int(command.args[4:])
            if referrer_id != user.id:
                create_referral(referrer_id, user.id)
        except ValueError:
            pass

    pending = get_pending_referral(user.id)
    if pending:
        await message.answer(
            "👋 Добро пожаловать в <b>StudyGo</b>!\n\n"
            "Чтобы активировать бонус за приглашение, "
            "подпишитесь на наш канал и нажмите кнопку ниже.",
            reply_markup=subscribe_kb(),
        )
        return

    await message.answer(
        "📚 <b>STUDYGO</b>\n\n"
        "Школьный AI-помощник с игровой системой.\n"
        "Решай задания, получай XP, поднимайся в рейтинге!",
        reply_markup=main_menu_kb(),
    )


@router.callback_query(F.data == "main")
async def cb_main(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await safe_edit(
        callback.message,
        "📚 <b>STUDYGO</b>\n\nВыберите действие:",
        reply_markup=main_menu_kb(),
    )
    await callback.answer()


@router.callback_query(F.data == "check_sub")
async def cb_check_sub(callback: CallbackQuery, bot: Bot):
    user_id = callback.from_user.id
    if await check_channel_subscription(bot, user_id):
        referrer = confirm_referral(user_id)
        text = "✅ Подписка подтверждена!\n"
        if referrer:
            text += "Реферал засчитан. Бонусы начислены 🎉\n"
        text += "\nДобро пожаловать в StudyGo!"
        await safe_edit(callback.message, text, reply_markup=main_menu_kb())
        grant_achievement(user_id, "first_task")
    else:
        await callback.answer("Вы ещё не подписаны на канал.", show_alert=True)
        return
    await callback.answer()
