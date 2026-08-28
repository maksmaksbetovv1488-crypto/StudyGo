"""XP packages, Premium, Stars payments."""

from aiogram import Router, F, Bot
from aiogram.types import (
    Message,
    CallbackQuery,
    LabeledPrice,
    PreCheckoutQuery,
    ContentType,
)

from keyboards import main_menu_kb, xp_packages_kb, premium_kb
from handlers.start import safe_edit
from database import (
    get_user,
    is_premium,
    change_xp,
    get_xp,
    add_premium_days,
    record_stars_purchase,
    grant_achievement,
)

router = Router()


@router.callback_query(F.data == "my_xp")
async def cb_my_xp(callback: CallbackQuery):
    user = get_user(callback.from_user.id)
    xp = user["xp"] if user else 0
    await safe_edit(
        callback.message,
        f"🟣 <b>Мой XP: {xp:,}</b>\n\n"
        f"Курс: 1 ⭐ = 10 XP\n"
        f"Выберите пакет для покупки:",
        reply_markup=xp_packages_kb(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("buy_xp:"))
async def cb_buy_xp(callback: CallbackQuery, bot: Bot):
    _, stars_s, xp_s = callback.data.split(":")
    stars, xp = int(stars_s), int(xp_s)
    prices = [LabeledPrice(label=f"{xp} XP", amount=stars)]
    await bot.send_invoice(
        chat_id=callback.from_user.id,
        title=f"{xp} XP",
        description=f"Пакет {xp} XP за {stars} Stars",
        payload=f"xp:{xp}",
        currency="XTR",
        prices=prices,
    )
    await callback.answer()


@router.callback_query(F.data == "premium")
async def cb_premium(callback: CallbackQuery):
    user = get_user(callback.from_user.id)
    status = "не активен"
    if user and user.get("premium_until") and is_premium(user["user_id"]):
        status = f"до {user['premium_until'].strftime('%d.%m.%Y %H:%M')}"
    await safe_edit(
        callback.message,
        f"💎 <b>Premium</b>\n\n"
        f"Статус: {status}\n\n"
        f"Преимущества:\n"
        f"♾️ Безлимитные AI-запросы\n"
        f"♾️ Безлимитные фото\n"
        f"📝 Создание тестов\n"
        f"0 XP за AI\n\n"
        f"Выберите срок:",
        reply_markup=premium_kb(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("buy_prem:"))
async def cb_buy_prem(callback: CallbackQuery, bot: Bot):
    _, days_s, stars_s = callback.data.split(":")
    days, stars = int(days_s), int(stars_s)
    prices = [LabeledPrice(label=f"Premium {days} дн.", amount=stars)]
    await bot.send_invoice(
        chat_id=callback.from_user.id,
        title=f"Premium {days} дней",
        description=f"Premium на {days} дней",
        payload=f"premium:{days}",
        currency="XTR",
        prices=prices,
    )
    await callback.answer()


@router.pre_checkout_query()
async def pre_checkout(query: PreCheckoutQuery):
    await query.answer(ok=True)


@router.message(F.content_type == ContentType.SUCCESSFUL_PAYMENT)
async def successful_payment(message: Message):
    payment = message.successful_payment
    user_id = message.from_user.id
    payload = payment.invoice_payload
    stars = payment.total_amount
    charge_id = payment.telegram_payment_charge_id

    if payload.startswith("xp:"):
        xp = int(payload.split(":")[1])
        change_xp(user_id, xp, "stars_purchase", f"{stars} Stars")
        record_stars_purchase(
            user_id, stars, "xp", xp,
            telegram_payment_charge_id=charge_id,
        )
        await message.answer(
            f"✅ Куплено <b>{xp:,} XP</b> за ⭐{stars}!\n"
            f"Баланс: <b>{get_xp(user_id):,} XP</b>",
            reply_markup=main_menu_kb(),
        )
    elif payload.startswith("premium:"):
        days = int(payload.split(":")[1])
        add_premium_days(user_id, days)
        record_stars_purchase(
            user_id, stars, "premium", days,
            telegram_payment_charge_id=charge_id,
        )
        grant_achievement(user_id, "first_premium")
        await message.answer(
            f"✅ Premium активирован на <b>{days} дней</b>!",
            reply_markup=main_menu_kb(),
  )
