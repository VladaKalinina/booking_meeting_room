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
from app.services.bookings import (
    BookingDraft,
    cancel_any_reservation,
    cancel_own_reservation,
    combine_date_time,
    create_booking,
    get_all_reservations,
    get_available_rooms,
    get_my_active_reservations,
    parse_equipment_type_ids,
    parse_time,
    validate_booking_time,
)
from app.services.equipment import (
    attach_equipment_to_room,
    create_equipment,
    create_equipment_type,
    get_equipment_items,
    get_equipment_types,
)
from app.services.rooms import create_room, deactivate_room, get_rooms
from app.services.schedule import (
    format_schedule,
    get_schedule_for_date,
    parse_schedule_date,
)
from app.services.users import (
    get_users,
    is_profile_complete,
    is_valid_email,
    register_or_update_user_profile,
    set_user_admin_status,
)
from app.states.equipment import (
    EquipmentAttachState,
    EquipmentCreationState,
    EquipmentTypeCreationState,
)
from app.states.booking import BookingCreationState
from app.states.registration import RegistrationState
from app.states.rooms import RoomCreationState
from app.states.schedule import ScheduleState

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
BOOKING_ROOM_PREFIX = "booking:room:"
RESERVATION_CANCEL_PREFIX = "reservation:cancel:"
ADMIN_RESERVATION_CANCEL_PREFIX = "admin:reservation:cancel:"
USER_ADMIN_SET_PREFIX = "users:admin:set:"
USER_ADMIN_UNSET_PREFIX = "users:admin:unset:"


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


def available_rooms_keyboard(rooms) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"#{room.room_id} {room.name}",
                    callback_data=f"{BOOKING_ROOM_PREFIX}{room.room_id}",
                )
            ]
            for room in rooms
        ]
    )


def format_equipment_type_prompt(types) -> str:
    if not types:
        return "Типы оборудования пока не добавлены. Напишите 'нет'."

    lines = ["Введите ID нужных типов оборудования через запятую или 'нет':"]
    lines.extend(f"#{item.type_id}: {item.name}" for item in types)
    return "\n".join(lines)


def format_available_rooms(rooms) -> str:
    if not rooms:
        return "Подходящих свободных комнат не найдено."

    lines = ["Подходящие свободные комнаты:"]
    for room in rooms:
        lines.append(
            f"#{room.room_id}: {room.name}, {room.location}, мест: {room.capacity}"
        )
    lines.append("\nВыберите комнату для подтверждения бронирования.")
    return "\n".join(lines)


def my_reservations_keyboard(reservations) -> InlineKeyboardMarkup | None:
    if not reservations:
        return None

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"Отменить #{reservation.reservation_id}",
                    callback_data=f"{RESERVATION_CANCEL_PREFIX}{reservation.reservation_id}",
                )
            ]
            for reservation in reservations
        ]
    )


def format_my_reservations(reservations) -> str:
    if not reservations:
        return "У вас пока нет активных бронирований."

    lines = ["Ваши активные бронирования:"]
    for reservation in reservations:
        start_at = reservation.start_datetime.strftime("%d.%m.%Y %H:%M")
        end_at = reservation.end_datetime.strftime("%H:%M")
        equipment = ", ".join(item.part_number for item in reservation.equipment_items) or "не указано"
        lines.append(
            f"\n#{reservation.reservation_id}: {start_at}-{end_at}\n"
            f"Комната: {reservation.room.name}\n"
            f"Цель: {reservation.purpose}\n"
            f"Оборудование: {equipment}\n"
            f"Статус: {reservation.status.name}"
        )

    return "\n".join(lines)


async def send_my_reservations(message: Message, session: AsyncSession, user) -> None:
    reservations = await get_my_active_reservations(session, organizer=user)
    await message.answer(
        format_my_reservations(reservations),
        reply_markup=my_reservations_keyboard(reservations),
    )


def all_reservations_keyboard(reservations) -> InlineKeyboardMarkup | None:
    active_reservations = [
        reservation for reservation in reservations if reservation.status_id in {1, 2}
    ]
    if not active_reservations:
        return None

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"Отменить #{reservation.reservation_id}",
                    callback_data=f"{ADMIN_RESERVATION_CANCEL_PREFIX}{reservation.reservation_id}",
                )
            ]
            for reservation in active_reservations
        ]
    )


def format_all_reservations(reservations) -> str:
    if not reservations:
        return "Бронирования пока не созданы."

    lines = ["Все бронирования:"]
    for reservation in reservations:
        start_at = reservation.start_datetime.strftime("%d.%m.%Y %H:%M")
        end_at = reservation.end_datetime.strftime("%H:%M")
        organizer = reservation.organizer.full_name
        lines.append(
            f"\n#{reservation.reservation_id}: {start_at}-{end_at}\n"
            f"Комната: {reservation.room.name}\n"
            f"Организатор: {organizer}\n"
            f"Цель: {reservation.purpose}\n"
            f"Статус: {reservation.status.name}"
        )

    return "\n".join(lines)


async def send_all_reservations(message: Message, session: AsyncSession) -> None:
    reservations = await get_all_reservations(session)
    await message.answer(
        format_all_reservations(reservations),
        reply_markup=all_reservations_keyboard(reservations),
    )


def users_management_keyboard(users, *, current_user_id: int) -> InlineKeyboardMarkup | None:
    buttons = []
    for user in users:
        if user.user_id == current_user_id:
            continue

        if user.is_admin:
            buttons.append(
                [
                    InlineKeyboardButton(
                        text=f"Снять права #{user.user_id}",
                        callback_data=f"{USER_ADMIN_UNSET_PREFIX}{user.user_id}",
                    )
                ]
            )
        else:
            buttons.append(
                [
                    InlineKeyboardButton(
                        text=f"Назначить админом #{user.user_id}",
                        callback_data=f"{USER_ADMIN_SET_PREFIX}{user.user_id}",
                    )
                ]
            )

    if not buttons:
        return None

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def format_users_text(users) -> str:
    if not users:
        return "Пользователи пока не зарегистрированы."

    lines = ["Пользователи:"]
    for user in users:
        role = "Администратор" if user.is_admin else "Сотрудник"
        lines.append(
            f"\n#{user.user_id}: {user.full_name}\n"
            f"Email: {user.email}\n"
            f"Telegram ID: {user.telegram_id}\n"
            f"Роль: {role}"
        )

    return "\n".join(lines)


async def send_users_management(
    message: Message,
    session: AsyncSession,
    current_user,
) -> None:
    users = await get_users(session)
    await message.answer(
        format_users_text(users),
        reply_markup=users_management_keyboard(
            users,
            current_user_id=current_user.user_id,
        ),
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


@router.message(F.text == BOOK_ROOM_TEXT)
async def start_booking_creation(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    user = await get_current_user(message, session)
    if not user or not is_profile_complete(user):
        await message.answer("Сначала завершите регистрацию через /start.")
        return

    await state.set_state(BookingCreationState.waiting_date)
    await message.answer(
        "Введите дату встречи в формате ДД.ММ.ГГГГ, например 26.04.2026.",
        reply_markup=cancel_keyboard(),
    )


@router.message(BookingCreationState.waiting_date)
async def process_booking_date(message: Message, state: FSMContext) -> None:
    try:
        booking_date = parse_schedule_date(message.text or "")
    except ValueError as error:
        await message.answer(str(error))
        return

    await state.update_data(booking_date=booking_date.isoformat())
    await state.set_state(BookingCreationState.waiting_start_time)
    await message.answer("Введите время начала в формате ЧЧ:ММ, например 09:30.")


@router.message(BookingCreationState.waiting_start_time)
async def process_booking_start_time(message: Message, state: FSMContext) -> None:
    try:
        start_time = parse_time(message.text or "")
    except ValueError as error:
        await message.answer(str(error))
        return

    await state.update_data(start_time=start_time.strftime("%H:%M"))
    await state.set_state(BookingCreationState.waiting_end_time)
    await message.answer("Введите время окончания в формате ЧЧ:ММ, например 10:30.")


@router.message(BookingCreationState.waiting_end_time)
async def process_booking_end_time(message: Message, state: FSMContext) -> None:
    try:
        end_time = parse_time(message.text or "")
    except ValueError as error:
        await message.answer(str(error))
        return

    data = await state.get_data()
    start_at = combine_date_time(
        parse_schedule_date(data["booking_date"]),
        parse_time(data["start_time"]),
    )
    end_at = combine_date_time(parse_schedule_date(data["booking_date"]), end_time)

    try:
        validate_booking_time(start_at, end_at)
    except ValueError as error:
        await message.answer(str(error))
        return

    await state.update_data(end_time=end_time.strftime("%H:%M"))
    await state.set_state(BookingCreationState.waiting_purpose)
    await message.answer("Введите цель встречи.")


@router.message(BookingCreationState.waiting_purpose)
async def process_booking_purpose(message: Message, state: FSMContext) -> None:
    purpose = " ".join((message.text or "").split())
    if not purpose:
        await message.answer("Цель встречи не может быть пустой.")
        return
    if len(purpose) > 200:
        await message.answer("Цель встречи должна быть не длиннее 200 символов.")
        return

    await state.update_data(purpose=purpose)
    await state.set_state(BookingCreationState.waiting_capacity)
    await message.answer("Введите минимальную вместимость комнаты числом.")


@router.message(BookingCreationState.waiting_capacity)
async def process_booking_capacity(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    capacity_text = (message.text or "").strip()
    if not capacity_text.isdigit():
        await message.answer("Вместимость нужно указать целым числом.")
        return

    capacity = int(capacity_text)
    if capacity <= 0:
        await message.answer("Вместимость должна быть положительным числом.")
        return

    await state.update_data(capacity=capacity)
    await state.set_state(BookingCreationState.waiting_equipment)
    await message.answer(format_equipment_type_prompt(await get_equipment_types(session)))


@router.message(BookingCreationState.waiting_equipment)
async def process_booking_equipment(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    try:
        equipment_type_ids = parse_equipment_type_ids(message.text or "")
    except ValueError as error:
        await message.answer(str(error))
        return

    known_type_ids = {item.type_id for item in await get_equipment_types(session)}
    unknown_type_ids = [type_id for type_id in equipment_type_ids if type_id not in known_type_ids]
    if unknown_type_ids:
        await message.answer(
            "Не найдены типы оборудования: "
            + ", ".join(f"#{type_id}" for type_id in unknown_type_ids)
        )
        return

    data = await state.get_data()
    booking_date = parse_schedule_date(data["booking_date"])
    start_at = combine_date_time(booking_date, parse_time(data["start_time"]))
    end_at = combine_date_time(booking_date, parse_time(data["end_time"]))

    available_rooms = await get_available_rooms(
        session,
        start_at=start_at,
        end_at=end_at,
        capacity=data["capacity"],
        equipment_type_ids=equipment_type_ids,
    )

    if not available_rooms:
        await state.clear()
        user = await get_current_user(message, session)
        await message.answer(
            "Подходящих свободных комнат не найдено. Попробуйте другой интервал или параметры.",
            reply_markup=main_menu_keyboard(is_admin=bool(user and user.is_admin)),
        )
        return

    await state.update_data(equipment_type_ids=equipment_type_ids)
    await state.set_state(BookingCreationState.waiting_room_confirmation)
    await message.answer(
        format_available_rooms(available_rooms),
        reply_markup=available_rooms_keyboard(available_rooms),
    )


@router.callback_query(
    BookingCreationState.waiting_room_confirmation,
    F.data.startswith(BOOKING_ROOM_PREFIX),
)
async def confirm_booking_room(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    user = await get_current_user_from_callback(callback, session)
    if not user:
        await callback.answer("Пользователь не найден.", show_alert=True)
        return

    room_id_text = callback.data.removeprefix(BOOKING_ROOM_PREFIX) if callback.data else ""
    if not room_id_text.isdigit():
        await callback.answer("Некорректная комната.", show_alert=True)
        return

    data = await state.get_data()
    booking_date = parse_schedule_date(data["booking_date"])
    draft = BookingDraft(
        start_at=combine_date_time(booking_date, parse_time(data["start_time"])),
        end_at=combine_date_time(booking_date, parse_time(data["end_time"])),
        purpose=data["purpose"],
        capacity=data["capacity"],
        equipment_type_ids=data["equipment_type_ids"],
    )

    try:
        reservation = await create_booking(
            session,
            organizer=user,
            room_id=int(room_id_text),
            draft=draft,
        )
        await session.commit()
    except ValueError as error:
        await session.rollback()
        await callback.answer(str(error), show_alert=True)
        return

    await state.clear()
    await callback.answer("Бронирование создано.")
    if callback.message:
        await callback.message.answer(
            "Бронирование создано.\n"
            f"Номер: #{reservation.reservation_id}\n"
            f"Дата: {booking_date.strftime('%d.%m.%Y')}\n"
            f"Время: {draft.start_at.strftime('%H:%M')}-{draft.end_at.strftime('%H:%M')}",
            reply_markup=main_menu_keyboard(is_admin=user.is_admin),
        )


@router.message(F.text == MY_RESERVATIONS_TEXT)
async def my_reservations(message: Message, session: AsyncSession) -> None:
    user = await get_current_user(message, session)
    if not user:
        await message.answer("Сначала зарегистрируйтесь через /start.")
        return

    await send_my_reservations(message, session, user)


@router.callback_query(F.data.startswith(RESERVATION_CANCEL_PREFIX))
async def cancel_reservation_callback(
    callback: CallbackQuery,
    session: AsyncSession,
) -> None:
    user = await get_current_user_from_callback(callback, session)
    if not user:
        await callback.answer("Пользователь не найден.", show_alert=True)
        return

    reservation_id_text = callback.data.removeprefix(RESERVATION_CANCEL_PREFIX) if callback.data else ""
    if not reservation_id_text.isdigit():
        await callback.answer("Некорректный номер бронирования.", show_alert=True)
        return

    try:
        reservation = await cancel_own_reservation(
            session,
            organizer=user,
            reservation_id=int(reservation_id_text),
        )
        await session.commit()
    except ValueError as error:
        await session.rollback()
        await callback.answer(str(error), show_alert=True)
        return

    await callback.answer(f"Бронирование #{reservation.reservation_id} отменено.")
    if callback.message:
        reservations = await get_my_active_reservations(session, organizer=user)
        await callback.message.edit_text(
            format_my_reservations(reservations),
            reply_markup=my_reservations_keyboard(reservations),
        )


@router.message(F.text == ALL_RESERVATIONS_TEXT)
async def all_reservations(message: Message, session: AsyncSession) -> None:
    if not await ensure_admin_message(message, session):
        return

    await send_all_reservations(message, session)


@router.callback_query(F.data.startswith(ADMIN_RESERVATION_CANCEL_PREFIX))
async def admin_cancel_reservation_callback(
    callback: CallbackQuery,
    session: AsyncSession,
) -> None:
    if not await ensure_admin_callback(callback, session):
        return

    reservation_id_text = (
        callback.data.removeprefix(ADMIN_RESERVATION_CANCEL_PREFIX)
        if callback.data
        else ""
    )
    if not reservation_id_text.isdigit():
        await callback.answer("Некорректный номер бронирования.", show_alert=True)
        return

    try:
        reservation = await cancel_any_reservation(
            session,
            reservation_id=int(reservation_id_text),
        )
        await session.commit()
    except ValueError as error:
        await session.rollback()
        await callback.answer(str(error), show_alert=True)
        return

    await callback.answer(f"Бронирование #{reservation.reservation_id} отменено.")
    if callback.message:
        reservations = await get_all_reservations(session)
        await callback.message.edit_text(
            format_all_reservations(reservations),
            reply_markup=all_reservations_keyboard(reservations),
        )


@router.message(F.text == USERS_MANAGEMENT_TEXT)
async def users_management(message: Message, session: AsyncSession) -> None:
    current_user = await ensure_admin_message(message, session)
    if not current_user:
        return

    await send_users_management(message, session, current_user)


@router.callback_query(
    F.data.startswith(USER_ADMIN_SET_PREFIX) | F.data.startswith(USER_ADMIN_UNSET_PREFIX)
)
async def toggle_user_admin_status(
    callback: CallbackQuery,
    session: AsyncSession,
) -> None:
    current_user = await ensure_admin_callback(callback, session)
    if not current_user:
        return

    callback_data = callback.data or ""
    make_admin = callback_data.startswith(USER_ADMIN_SET_PREFIX)
    prefix = USER_ADMIN_SET_PREFIX if make_admin else USER_ADMIN_UNSET_PREFIX
    user_id_text = callback_data.removeprefix(prefix)

    if not user_id_text.isdigit():
        await callback.answer("Некорректный идентификатор пользователя.", show_alert=True)
        return

    target_user_id = int(user_id_text)
    if target_user_id == current_user.user_id:
        await callback.answer("Нельзя изменить собственную роль через этот раздел.", show_alert=True)
        return

    try:
        target_user = await set_user_admin_status(
            session,
            user_id=target_user_id,
            is_admin=make_admin,
        )
        await session.commit()
    except ValueError as error:
        await session.rollback()
        await callback.answer(str(error), show_alert=True)
        return

    role_text = "администратор" if target_user.is_admin else "сотрудник"
    await callback.answer(f"Пользователь #{target_user.user_id}: {role_text}.")

    if callback.message:
        users = await get_users(session)
        await callback.message.edit_text(
            format_users_text(users),
            reply_markup=users_management_keyboard(
                users,
                current_user_id=current_user.user_id,
            ),
        )


@router.message(F.text == SCHEDULE_TEXT)
async def start_schedule_view(message: Message, state: FSMContext) -> None:
    await state.set_state(ScheduleState.waiting_date)
    await message.answer(
        "Введите дату расписания в формате ДД.ММ.ГГГГ, например 26.04.2026.\n"
        "Также можно написать: сегодня или завтра.",
        reply_markup=cancel_keyboard(),
    )


@router.message(ScheduleState.waiting_date)
async def process_schedule_date(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    try:
        schedule_date = parse_schedule_date(message.text or "")
    except ValueError as error:
        await message.answer(str(error))
        return

    schedule = await get_schedule_for_date(session, schedule_date=schedule_date)
    await state.clear()
    user = await get_current_user(message, session)
    await message.answer(
        format_schedule(schedule_date, schedule),
        reply_markup=main_menu_keyboard(is_admin=bool(user and user.is_admin)),
    )


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


@router.message(F.text == ANALYTICS_TEXT)
async def admin_feature_stub(message: Message) -> None:
    await message.answer("Административный сценарий добавим на следующих этапах.")


@router.message()
async def unknown_message(message: Message) -> None:
    await message.answer("Не понял команду. Выберите действие в меню или отправьте /start.")
