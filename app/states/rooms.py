from aiogram.fsm.state import State, StatesGroup


class RoomCreationState(StatesGroup):
    waiting_name = State()
    waiting_location = State()
    waiting_capacity = State()
