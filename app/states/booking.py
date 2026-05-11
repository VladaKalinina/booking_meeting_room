from aiogram.fsm.state import State, StatesGroup


class BookingCreationState(StatesGroup):
    waiting_date = State()
    waiting_start_time = State()
    waiting_end_time = State()
    waiting_purpose = State()
    waiting_capacity = State()
    waiting_equipment = State()
    waiting_room_confirmation = State()


class BookingEditState(StatesGroup):
    waiting_single_date = State()
    waiting_single_start_time = State()
    waiting_single_end_time = State()
    waiting_single_purpose = State()
    waiting_single_capacity = State()
    waiting_single_equipment = State()
    waiting_date = State()
    waiting_start_time = State()
    waiting_end_time = State()
    waiting_purpose = State()
    waiting_capacity = State()
    waiting_equipment = State()
    waiting_room_confirmation = State()


class ParticipantManagementState(StatesGroup):
    waiting_emails = State()
