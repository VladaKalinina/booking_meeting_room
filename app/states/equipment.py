from aiogram.fsm.state import State, StatesGroup


class EquipmentTypeCreationState(StatesGroup):
    waiting_name = State()


class EquipmentCreationState(StatesGroup):
    waiting_type_id = State()
    waiting_part_number = State()


class EquipmentAttachState(StatesGroup):
    waiting_room_id = State()
    waiting_equipment_id = State()


class EquipmentDetachState(StatesGroup):
    waiting_room_id = State()
    waiting_equipment_id = State()
