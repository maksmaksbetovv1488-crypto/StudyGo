"""AI features: text, photo, explain, test, check."""

from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from keyboards import main_menu_kb, back_kb
from states import AIStates
from ai_service import call_gemini
from handlers.start import safe_edit
from database import (
    is_blocked,
    is_premium,
    change_xp,
    get_xp,
    get_setting_int,
    log_ai_usage,
    add_score,
    add_daily_score,
    grant_achievement,
    ensure_user,
)

router = Router()


async def spend_xp_or_premium(user_id: int, cost_key: str, request_type: str) -> tuple[bool, str]:
    if is_premium(user_id):
        log_ai_usage(user_id, request_type, xp_spent=0, is_premium=True)
        return True, ""
    cost = get_setting_int(cost_key, 20)
    try:
        change_xp(user_id, -cost, "ai_request", request_type)
        log_ai_usage(user_id, request_type, xp_spent=cost, is_premium=False)
        return True, ""
    except ValueError:
        return False, (
            f"Недостаточно XP. Нужно <b>{cost} XP</b>.\n"
            f"У вас: <b>{get_xp(user_id)} XP</b>\n\n"
            f"Купите XP за Stars или выполните задания."
        )


@router.callback_query(F.data == "ai_helper")
async def cb_ai_helper(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AIStates.waiting_question)
    await safe_edit(
        callback.message,
        "🧠 <b>AI-помощник</b>\n\n"
        "Напишите вопрос или задачу.\n"
        "Например: <i>Реши 2x + 5 = 17</i>\n\n"
        "Стоимость: 10–50 XP (или бесплатно с Premium)",
        reply_markup=back_kb(),
    )
    await callback.answer()


@router.message(AIStates.waiting_question)
async def process_ai_question(message: Message, state: FSMContext):
    user_id = message.from_user.id
    if is_blocked(user_id):
        return
    ok, err = await spend_xp_or_premium(user_id, "cost_normal_task", "text")
    if not ok:
        await message.answer(err, reply_markup=main_menu_kb())
        await state.clear()
        return

    await message.answer("⏳ Решаю...")
    answer = await call_gemini(message.text)
    await message.answer(answer, reply_markup=main_menu_kb())
    add_score(user_id, get_setting_int("score_solve_task", 5))
    add_daily_score(user_id, get_setting_int("ds_solve_task", 5))
    grant_achievement(user_id, "first_task")
    await state.clear()


@router.callback_query(F.data == "ai_photo")
async def cb_ai_photo(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AIStates.waiting_photo)
    await safe_edit(
        callback.message,
        "📸 <b>Решить по фото</b>\n\n"
        "Отправьте фотографию задания.\n"
        "Стоимость: 30 XP (или бесплатно с Premium)",
        reply_markup=back_kb(),
    )
    await callback.answer()


@router.message(AIStates.waiting_photo, F.photo)
async def process_photo(message: Message, state: FSMContext, bot: Bot):
    user_id = message.from_user.id
    if is_blocked(user_id):
        return
    ok, err = await spend_xp_or_premium(user_id, "cost_photo_task", "photo")
    if not ok:
        await message.answer(err, reply_markup=main_menu_kb())
        await state.clear()
        return

    await message.answer("⏳ Распознаю и решаю...")
    photo = message.photo[-1]
    file = await bot.get_file(photo.file_id)
    file_bytes = await bot.download_file(file.file_path)
    image_data = file_bytes.read()

    answer = await call_gemini(
        "Распознай задание на фото и реши его. "
        "Если несколько заданий — пронумеруй. "
        "Если что-то нечитаемо — укажи явно.",
        image_bytes=image_data,
    )
    await message.answer(answer, reply_markup=main_menu_kb())
    add_score(user_id, get_setting_int("score_solve_task", 5))
    add_daily_score(user_id, get_setting_int("ds_photo", 7))
    grant_achievement(user_id, "first_task")
    await state.clear()


@router.message(AIStates.waiting_photo)
async def process_photo_no_photo(message: Message):
    await message.answer("Пожалуйста, отправьте именно фотографию.")


@router.callback_query(F.data == "ai_explain")
async def cb_ai_explain(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AIStates.waiting_topic)
    await safe_edit(
        callback.message,
        "📚 <b>Объяснить тему</b>\n\n"
        "Напишите тему, например: <i>квадратные уравнения</i>\n"
        "Стоимость: 20 XP",
        reply_markup=back_kb(),
    )
    await callback.answer()


@router.message(AIStates.waiting_topic)
async def process_topic(message: Message, state: FSMContext):
    user_id = message.from_user.id
    ok, err = await spend_xp_or_premium(user_id, "cost_explain_topic", "explain")
    if not ok:
        await message.answer(err, reply_markup=main_menu_kb())
        await state.clear()
        return

    await message.answer("⏳ Готовлю объяснение...")
    prompt = (
        f"Объясни тему школьнику: {message.text}\n\n"
        "Используй структуру:\n"
        "📚 Простыми словами\n🧠 Главное\n🔢 Пример\n"
        "⚠️ Частые ошибки\n🎯 Проверь себя"
    )
    answer = await call_gemini(prompt)
    await message.answer(answer, reply_markup=main_menu_kb())
    add_daily_score(user_id, get_setting_int("ds_explain", 5))
    await state.clear()


@router.callback_query(F.data == "ai_test")
async def cb_ai_test(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AIStates.waiting_test_params)
    await safe_edit(
        callback.message,
        "📝 <b>Создать тест</b>\n\n"
        "Напишите в формате:\n"
        "<code>предмет | тема | класс | кол-во вопросов | сложность</code>\n\n"
        "Пример: <i>математика | квадратные уравнения | 8 | 5 | средняя</i>\n"
        "Стоимость: 30 XP",
        reply_markup=back_kb(),
    )
    await callback.answer()


@router.message(AIStates.waiting_test_params)
async def process_test(message: Message, state: FSMContext):
    user_id = message.from_user.id
    ok, err = await spend_xp_or_premium(user_id, "cost_create_test", "test")
    if not ok:
        await message.answer(err, reply_markup=main_menu_kb())
        await state.clear()
        return

    await message.answer("⏳ Создаю тест...")
    prompt = (
        f"Создай школьный тест по параметрам: {message.text}\n"
        "Формат: нумерованные вопросы с вариантами A B C D. "
        "В конце укажи правильные ответы отдельно."
    )
    answer = await call_gemini(prompt)
    await message.answer(answer, reply_markup=main_menu_kb())
    add_daily_score(user_id, get_setting_int("ds_create_test", 7))
    await state.clear()


@router.callback_query(F.data == "ai_check")
async def cb_ai_check(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AIStates.waiting_check_answer)
    await safe_edit(
        callback.message,
        "✅ <b>Проверить ответ</b>\n\n"
        "Пришлите условие задачи и свой ответ.\n"
        "Стоимость: 10 XP",
        reply_markup=back_kb(),
    )
    await callback.answer()


@router.message(AIStates.waiting_check_answer)
async def process_check(message: Message, state: FSMContext):
    user_id = message.from_user.id
    ok, err = await spend_xp_or_premium(user_id, "cost_check_answer", "check")
    if not ok:
        await message.answer(err, reply_markup=main_menu_kb())
        await state.clear()
        return

    await message.answer("⏳ Проверяю...")
    prompt = (
        f"Проверь ответ ученика:\n{message.text}\n\n"
        "Укажи: правильность, ошибку (если есть), причину, "
        "правильный способ решения."
    )
    answer = await call_gemini(prompt)
    await message.answer(answer, reply_markup=main_menu_kb())
    await state.clear()


@router.message(F.text)
async def fallback_text(message: Message, state: FSMContext):
    """Free text → AI if not in FSM state."""
    current = await state.get_state()
    if current:
        return
    user_id = message.from_user.id
    if is_blocked(user_id):
        return
    ensure_user(user_id, message.from_user.username, message.from_user.first_name)
    ok, err = await spend_xp_or_premium(user_id, "cost_normal_task", "text")
    if not ok:
        await message.answer(err, reply_markup=main_menu_kb())
        return
    await message.answer("⏳ Решаю...")
    answer = await call_gemini(message.text)
    await message.answer(answer, reply_markup=main_menu_kb())
    add_score(user_id, get_setting_int("score_solve_task", 5))
    add_daily_score(user_id, get_setting_int("ds_solve_task", 5))
