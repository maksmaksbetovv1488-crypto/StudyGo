"""Подписки за Telegram Stars."""

from aiogram import Router, F, Bot
from aiogram.types import (
    Message, CallbackQuery, LabeledPrice, PreCheckoutQuery, ContentType,
)

from keyboards import main_menu_kb, subscription_kb
from handlers.start import safe_edit
from plans import PLANS, plans_shop_text, plan_title
from database import (
    get_user, get_active_plan, add_plan_days, record_stars_purchase,
    get_used_today, get_daily_limit,
)

router = Router()


@router.callback_query(F.data == "subscription")
async def cb_subscription(callback: CallbackQuery, bot: Bot):
    uid = callback.from_user.id
    plan = get_active_plan(uid)
    user = get_user(uid)
    until = user.get("plan_until") if user else None
    until_s = until.strftime("%d.%m.%Y") if until else "—"
    used = get_used_today(uid)
    # bio check light - without bot for limit display base
    limit = get_daily_limit(uid, has_bio=False)

    text = plans_shop_text()
    text = (
        f"📌 Сейчас: <b>{plan_title(plan)}</b>"
        + (f" до {until_s}" if plan != "free" else "")
        + f"\n📊 Сегодня: <b>{used}/{limit}</b> (+бонусы при проверке)\n\n"
        + text
    )
    await safe_edit(callback.message, text, reply_markup=subscription_kb())
    await callback.answer()


@router.callback_query(F.data.startswith("buy_plan:"))
async def cb_buy_plan(callback: CallbackQuery, bot: Bot):
    plan_id = callback.data.split(":")[1]
    p = PLANS.get(plan_id)
    if not p or p["stars"] <= 0:
        await callback.answer("Недоступно", show_alert=True)
        return
    stars = p["stars"]
    prices = [LabeledPrice(label=f"{p['title']} 30 дн.", amount=stars)]
    await bot.send_invoice(
        chat_id=callback.from_user.id,
        title=f"StudyGo {p['title']}",
        description=f"{p['title']} на 30 дней — {p['limit']} запросов/день",
        payload=f"plan:{plan_id}:30",
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

    if payload.startswith("plan:"):
        parts = payload.split(":")
        plan_id = parts[1]
        days = int(parts[2]) if len(parts) > 2 else 30
        add_plan_days(user_id, plan_id, days)
        record_stars_purchase(
            user_id, stars, "plan", days,
            telegram_payment_charge_id=charge_id,
        )
        await message.answer(
            f"✅ <b>{plan_title(plan_id)}</b> на <b>{days} дн.</b> активирован!",
            reply_markup=main_menu_kb(),
        )
