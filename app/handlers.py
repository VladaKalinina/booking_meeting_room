from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.users import get_user_by_telegram_id
from app.services.equipment import (
    attach_equipment_to_room,
    create_equipment,
    create_equipment_type,
    get_equipment_items,
    get_equipment_types,
)
from app.services.rooms import create_room, deactivate_room, get_rooms
from app.services.users import (
    is_profile_complete,
    is_valid_email,
    register_or_update_user_profile,
)
from app.states.equipment import (
    EquipmentAttachState,
    EquipmentCreationState,
    EquipmentTypeCreationState,
)
from app.states.registration import RegistrationState
from app.states.rooms import RoomCreationState

router = Router()

BOOK_ROOM_TEXT = "Забронировать"
MY_RESERVATIONS_TEXT = "Мои бронирования"
SCHEDULE_TEXT = "Расписание"
HELP_TEXT = "Помощь"
ALL_RESERVATIONS_TEXT = "Все бронирования"
ROOMS_MANAGEMENT_TEXT = "Управление комнатами"
EQUIPMENT_MANAGEMENT_TEXT = "Управление оборудованием"
ANALYTICS_TEXT = "Аналитика"
USERS_MANAGEMENT_TEXT = "Управление пользователями"
CANCEL_TEXT = "Отмена"

ROOM_ADD_CALLBACK = "rooms:add"
ROOM_DEACTIVATE_PREFIX = "rooms:deactivate:"
EQUIPMENT_TYPE_ADD_CALLBACK = "equipment:type:add"
EQUIPMENT_ADD_CALLBACK = "equipment:add"
EQUIPMENT_ATTACH_CALLBACK = "equipment:attach"


def main_menu_keyboard(*, is_admin: bool = False) -> ReplyKeyboardMarkup:
    keyboard = [
        [KeyboardButton(text=BOOK_ROOM_TEXT), KeyboardButton(text=MY_RESERVATIONS_TEXT)],
        [KeyboardButton(text=SCHEDULE_TEXT), KeyboardButton(text=HELP_TEXT)],
    ]

    if is_admin:
        keyboard.extend(
            [
                [
                    KeyboardButton(text=ALL_RESERVATIONS_TEXT),
                    KeyboardButton(text=ROOMS_MANAGEMENT_TEXT),
                ],
                [
                    KeyboardButton(text=EQUIPMENT_MANAGEMENT_TEXT),
                    KeyboardButton(text=ANALYTICS_TEXT),
                ],
                [KeyboardButton(text=USERS_MANAGEMENT_TEXT)],
            ]
        )

    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        input_field_placeholder="Выберите действие",
    )


def cancel_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=CANCEL_TEXT)]],
        resize_keyboard=True,
        input_field_placeholder="Можно отменить сценарий",
    )


async def send_main_menu(message: Message, *, full_name: str, is_admin: bool) -> None:
    role_text = "Администратор" if is_admin else "Сотрудник"
    await message.answer(
        f"Привет, {full_name}!\n\nТвоя роль: {role_text}.\nВыбери действие в меню.",
        reply_markup=main_menu_keyboard(is_admin=is_admin),
    )


async def get_current_user(message: Message, session: AsyncSession):
    if not message.from_user:
        return None
    return await get_user_by_telegram_id(session, message.from_user.id)


async def get_current_user_from_callback(callback: CallbackQuery, session: AsyncSession):
    return await get_user_by_telegram_id(session, callback.from_user.id)


async def ensure_admin_message(message: Message, session: AsyncSession):
    user = await get_current_user(message, session)
    if not user or not user.is_admin:
        await message.answer("Недостаточно прав для выполнения действия.")
        return None
    return user


async def ensure_admin_callback(callback: CallbackQuery, session: AsyncSession):
    user = await get_current_user_from_callback(callback, session)
    if not user or not user.is_admin:
        await callback.answer("Недостаточно прав.", show_alert=True)
        return None
    return user


def rooms_management_keyboard(rooms) -> InlineKeyboardMarkup:
    keyboard = [[InlineKeyboardButton(text="Добавить комнату", callback_data=ROOM_ADD_CALLBACK)]]

    for room in rooms:
        if room.is_active:
            keyboard.append(
                [
                    InlineKeyboardButton(
                        text=f"Деактивировать #{room.room_id}",
                        callback_data=f"{ROOM_DEACTIVATE_PREFIX}{room.room_id}",
                    )
                ]
            )

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def format_rooms_text(rooms) -> str:
    if not rooms:
        return "Переговорные комнаты пока не добавлены."

    lines = ["Переговорные комнаты:"]
    for room in rooms:
        status = "активна" if room.is_active else "неактивна"
        lines.append(
            f"#{room.room_id}: {room.name}, {room.location}, "
            f"вместимость: {room.capacity}, статус: {status}"
        )
    return "\n".join(lines)


async def send_rooms_management(message: Message, session: AsyncSession) -> None:
    rooms = await get_rooms(session)
    await message.answer(format_rooms_text(rooms), reply_markup=rooms_management_keyboard(rooms))


def equipment_management_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Добавить тип", callback_data=EQUIPMENT_TYPE_ADD_CALLBACK)],
            [InlineKeyboardButton(text="Добавить оборудование", callback_data=EQUIPMENT_ADD_CALLBACK)],
            [InlineKeyboardButton(text="Привязать к комнате", callback_data=EQUIPMENT_ATTACH_CALLBACK)],
        ]
    )


def format_equipment_text(types, equipment_items) -> str:
    lines = ["Оборудование:"]

    if types:
        lines.append("\nТипы:")
        for item in types:
            lines.append(f"#{item.type_id}: {item.name}")
    else:
        lines.append("\nТипы оборудования пока не добавлены.")

    if equipment_items:
        lines.append("\nЭкземпляры:")
        for item in equipment_items:
            room_names = ", ".join(room.name for room in item.rooms) or "не привязано"
            lines.append(
                f"#{item.equipment_id}: {item.type.name}, "
                f"инв. номер: {item.part_number}, комнаты: {room_names}"
            )
    else:
        lines.append("\nОборудование пока не добавлено.")

    return "\n".join(lines)


async def send_equipment_management(message: Message, session: AsyncSession) -> None:
    types = await get_equipment_types(session)
    equipment_items = await get_equipment_items(session)
    await message.answer(
        format_equipment_text(types, equipment_items),
        reply_markup=equipment_management_keyboard(),
    )


@router.message(CommandStart())
async def start(message: Message, session: AsyncSession, state: FSMContext) -> None:
    if not message.from_user:
        await message.answer("Не удалось определить пользователя Telegram.")
        return

    await state.clear()
    user = await get_user_by_telegram_id(session, message.from_user.id)
    if user and is_profile_complete(user):
        await send_main_menu(message, full_name=user.full_name, is_admin=user.is_admin)
        return

    await state.set_state(RegistrationState.waiting_full_name)
    await message.answer(
        "Давай зарегистрируем тебя в системе бронирования.\n\n"
        "Введите ФИО полностью, например: Иванов Иван Иванович.",
        reply_markup=cancel_keyboard(),
    )


@router.message(Command("cancel"))
@router.message(F.text == CANCEL_TEXT)
async def cancel_scenario(message: Message, state: FSMContext) -> None:
    current_state = await state.get_state()
    await state.clear()

    if current_state:
        await message.answer(
            "Сценарий отменён. Чтобы начать заново, отправьте /start.",
            reply_markup=ReplyKeyboardRemove(),
        )
    else:
        await message.answer("Активного сценария нет. Отправьте /start.")


@router.message(RegistrationState.waiting_full_name)
async def process_full_name(message: Message, state: FSMContext) -> None:
    full_name = (message.text or "").strip()

    if len(full_name.split()) < 2:
        await message.answer("Введите ФИО минимум из двух слов, например: Иванов Иван.")
        return
    if len(full_name) > 150:
        await message.answer("ФИО слишком длинное. Максимум 150 символов.")
        return

    await state.update_data(full_name=full_name)
    await state.set_state(RegistrationState.waiting_email)
    await message.answer("Теперь введите корпоративный email.")


@router.message(RegistrationState.waiting_email)
async def process_email(message: Message, session: AsyncSession, state: FSMContext) -> None:
    if not message.from_user:
        await message.answer("Не удалось определить пользователя Telegram.")
        return

    email = (message.text or "").strip()
    if not is_valid_email(email):
        await message.answer("Email выглядит некорректно. Попробуйте ещё раз.")
        return

    data = await state.get_data()
    try:
        user, _ = await register_or_update_user_profile(
            session,
            telegram_id=message.from_user.id,
            full_name=data["full_name"],
            email=email,
        )
        await session.commit()
    except ValueError as error:
        await session.rollback()
        await message.answer(str(error))
        return

    await state.clear()
    await message.answer("Регистрация завершена.", reply_markup=ReplyKeyboardRemove())
    await send_main_menu(message, full_name=user.full_name, is_admin=user.is_admin)


@router.message(F.text == ROOMS_MANAGEMENT_TEXT)
async def rooms_management(message: Message, session: AsyncSession) -> None:
    if not await ensure_admin_message(message, session):
        return
    await send_rooms_management(message, session)


@router.callback_query(F.data == ROOM_ADD_CALLBACK)
async def start_room_creation(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    if not await ensure_admin_callback(callback, session):
        return

    await state.set_state(RoomCreationState.waiting_name)
    await callback.answer()
    if callback.message:
        await callback.message.answer("Введите название переговорной комнаты.", reply_markup=cancel_keyboard())


@router.message(RoomCreationState.waiting_name)
async def process_room_name(message: Message, state: FSMContext) -> None:
    name = (message.text or "").strip()
    if not name:
        await message.answer("Название не может быть пустым.")
        return
    if len(name) > 100:
        await message.answer("Название должно быть не длиннее 100 символов.")
        return

    await state.update_data(room_name=name)
    await state.set_state(RoomCreationState.waiting_location)
    await message.answer("Введите расположение комнаты, например: 3 этаж, офис 305.")


@router.message(RoomCreationState.waiting_location)
async def process_room_location(message: Message, state: FSMContext) -> None:
    location = (message.text or "").strip()
    if not location:
        await message.answer("Расположение не может быть пустым.")
        return
    if len(location) > 100:
        await message.answer("Расположение должно быть не длиннее 100 символов.")
        return

    await state.update_data(room_location=location)
    await state.set_state(RoomCreationState.waiting_capacity)
    await message.answer("Введите вместимость комнаты числом.")


@router.message(RoomCreationState.waiting_capacity)
async def process_room_capacity(message: Message, session: AsyncSession, state: FSMContext) -> None:
    capacity_text = (message.text or "").strip()
    if not capacity_text.isdigit():
        await message.answer("Вместимость нужно указать целым числом.")
        return

    data = await state.get_data()
    try:
        room = await create_room(
            session,
            name=data["room_name"],
            location=data["room_location"],
            capacity=int(capacity_text),
        )
        await session.commit()
    except ValueError as error:
        await session.rollback()
        await message.answer(str(error))
        return

    await state.clear()
    await message.answer(f"Комната #{room.room_id} добавлена.", reply_markup=ReplyKeyboardRemove())
    await send_rooms_management(message, session)


@router.callback_query(F.data.startswith(ROOM_DEACTIVATE_PREFIX))
async def deactivate_room_callback(callback: CallbackQuery, session: AsyncSession) -> None:
    if not await ensure_admin_callback(callback, session):
        return

    room_id_text = callback.data.removeprefix(ROOM_DEACTIVATE_PREFIX) if callback.data else ""
    if not room_id_text.isdigit():
        await callback.answer("Некорректный идентификатор комнаты.", show_alert=True)
        return

    try:
        room = await deactivate_room(session, int(room_id_text))
        await session.commit()
    except ValueError as error:
        await session.rollback()
        await callback.answer(str(error), show_alert=True)
        return

    await callback.answer(f"Комната #{room.room_id} деактивирована.")
    if callback.message:
        rooms = await get_rooms(session)
        await callback.message.edit_text(
            format_rooms_text(rooms),
            reply_markup=rooms_management_keyboard(rooms),
        )


@router.message(F.text == EQUIPMENT_MANAGEMENT_TEXT)
async def equipment_management(message: Message, session: AsyncSession) -> None:
    if not await ensure_admin_message(message, session):
        return
    await send_equipment_management(message, session)


@router.callback_query(F.data == EQUIPMENT_TYPE_ADD_CALLBACK)
async def start_equipment_type_creation(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    if not await ensure_admin_callback(callback, session):
        return

    await state.set_state(EquipmentTypeCreationState.waiting_name)
    await callback.answer()
    if callback.message:
        await callback.message.answer("Введите название типа оборудования.", reply_markup=cancel_keyboard())


@router.message(EquipmentTypeCreationState.waiting_name)
async def process_equipment_type_name(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    try:
        equipment_type = await create_equipment_type(session, name=message.text or "")
        await session.commit()
    except ValueError as error:
        await session.rollback()
        await message.answer(str(error))
        return

    await state.clear()
    await message.answer(f"Тип оборудования #{equipment_type.type_id} добавлен.", reply_markup=ReplyKeyboardRemove())
    await send_equipment_management(message, session)


@router.callback_query(F.data == EQUIPMENT_ADD_CALLBACK)
async def start_equipment_creation(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    if not await ensure_admin_callback(callback, session):
        return

    types = await get_equipment_types(session)
    if not types:
        await callback.answer("Сначала добавьте тип оборудования.", show_alert=True)
        return

    await state.set_state(EquipmentCreationState.waiting_type_id)
    await callback.answer()
    if callback.message:
        await callback.message.answer(
            "Введите ID типа оборудования:\n"
            + "\n".join(f"#{item.type_id}: {item.name}" for item in types),
            reply_markup=cancel_keyboard(),
        )


@router.message(EquipmentCreationState.waiting_type_id)
async def process_equipment_type_id(message: Message, state: FSMContext) -> None:
    type_id_text = (message.text or "").strip()
    if not type_id_text.isdigit():
        await message.answer("Введите ID типа оборудования числом.")
        return

    await state.update_data(equipment_type_id=int(type_id_text))
    await state.set_state(EquipmentCreationState.waiting_part_number)
    await message.answer("Введите инвентарный номер оборудования.")


@router.message(EquipmentCreationState.waiting_part_number)
async def process_equipment_part_number(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    data = await state.get_data()
    try:
        equipment = await create_equipment(
            session,
            type_id=data["equipment_type_id"],
            part_number=message.text or "",
        )
        await session.commit()
    except ValueError as error:
        await session.rollback()
        await message.answer(str(error))
        return

    await state.clear()
    await message.answer(f"Оборудование #{equipment.equipment_id} добавлено.", reply_markup=ReplyKeyboardRemove())
    await send_equipment_management(message, session)


@router.callback_query(F.data == EQUIPMENT_ATTACH_CALLBACK)
async def start_equipment_attach(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    if not await ensure_admin_callback(callback, session):
        return

    rooms = await get_rooms(session)
    if not rooms:
        await callback.answer("Сначала добавьте комнату.", show_alert=True)
        return

    await state.set_state(EquipmentAttachState.waiting_room_id)
    await callback.answer()
    if callback.message:
        await callback.message.answer(
            "Введите ID комнаты:\n"
            + "\n".join(f"#{room.room_id}: {room.name}" for room in rooms),
            reply_markup=cancel_keyboard(),
        )


@router.message(EquipmentAttachState.waiting_room_id)
async def process_attach_room_id(message: Message, state: FSMContext) -> None:
    room_id_text = (message.text or "").strip()
    if not room_id_text.isdigit():
        await message.answer("Введите ID комнаты числом.")
        return

    await state.update_data(attach_room_id=int(room_id_text))
    await state.set_state(EquipmentAttachState.waiting_equipment_id)
    await message.answer("Введите ID оборудования.")


@router.message(EquipmentAttachState.waiting_equipment_id)
async def process_attach_equipment_id(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    equipment_id_text = (message.text or "").strip()
    if not equipment_id_text.isdigit():
        await message.answer("Введите ID оборудования числом.")
        return

    data = await state.get_data()
    try:
        await attach_equipment_to_room(
            session,
            room_id=data["attach_room_id"],
            equipment_id=int(equipment_id_text),
        )
        await session.commit()
    except ValueError as error:
        await session.rollback()
        await message.answer(str(error))
        return

    await state.clear()
    await message.answer("Оборудование привязано к комнате.", reply_markup=ReplyKeyboardRemove())
    await send_equipment_management(message, session)


@router.message(F.text == HELP_TEXT)
async def help_message(message: Message) -> None:
    await message.answer(
        "Бот подключен к базе данных. Сейчас доступны регистрация, управление комнатами и оборудованием."
    )


@router.message(F.text.in_({BOOK_ROOM_TEXT, MY_RESERVATIONS_TEXT, SCHEDULE_TEXT}))
async def feature_stub(message: Message) -> None:
    await message.answer(
        "Этот сценарий уже есть в меню. Следующим шагом реализуем расписание и бронирования."
    )


@router.message(F.text.in_({ALL_RESERVATIONS_TEXT, ANALYTICS_TEXT, USERS_MANAGEMENT_TEXT}))
async def admin_feature_stub(message: Message) -> None:
    await message.answer("Административный сценарий добавим на следующих этапах.")


@router.message()
async def unknown_message(message: Message) -> None:
    await message.answer("Не понял команду. Выберите действие в меню или отправьте /start.")
