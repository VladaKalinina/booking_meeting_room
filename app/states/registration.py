from aiogram.fsm.state import State, StatesGroup


class RegistrationState(StatesGroup):
    waiting_full_name = State()
    waiting_email = State()
