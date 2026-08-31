from aiogram.fsm.state import State, StatesGroup


class AIStates(StatesGroup):
    waiting_question = State()
    waiting_photo = State()
    waiting_topic = State()
    waiting_test_params = State()
    waiting_check_answer = State()
    waiting_conspect = State()
    waiting_error = State()
    waiting_week = State()
    waiting_hard = State()
    waiting_big = State()


class AdminStates(StatesGroup):
    search_user = State()
    give_plan = State()
    give_days = State()
    broadcast_text = State()
    broadcast_confirm = State()
