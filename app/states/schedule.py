from aiogram.fsm.state import State, StatesGroup


class ScheduleState(StatesGroup):
    waiting_date = State()
