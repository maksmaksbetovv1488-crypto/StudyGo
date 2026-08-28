"""StudyGo — FSM states."""

from aiogram.fsm.state import State, StatesGroup


class AIStates(StatesGroup):
    waiting_question = State()
    waiting_photo = State()
    waiting_topic = State()
    waiting_test_params = State()
    waiting_check_answer = State()


class AdminStates(StatesGroup):
    search_user = State()
    give_xp = State()
    take_xp = State()
    give_premium = State()
    broadcast_text = State()
    broadcast_confirm = State()
