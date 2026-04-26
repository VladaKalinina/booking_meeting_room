from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import KeyboardButton, Message, ReplyKeyboardMarkup, ReplyKeyboardRemove
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.users import get_user_by_telegram_id
from app.services.users import (
    is_profile_complete,
    is_valid_email,
    register_or_update_user_profile,
)
from app.states.registration import RegistrationState

router = Router()

BOOK_ROOM_TEXT = "Забронировать"
MY_RESERVATIONS_TEXT = "Мои бронирования"
SCHEDULE_TEXT = "Расписание"
HELP_TEXT = "Помощь"
ALL_RESERVATIONS_TEXT = "Все бронирования"
ROOMS_MANAGEMENT_TEXT = "Управление комнатами"
ANALYTICS_TEXT = "Аналитика"
USERS_MANAGEMENT_TEXT = "Управление пользователями"
CANCEL_TEXT = "Отмена"


def main_menu_keyboard(*, is_admin: bool = False) -> ReplyKeyboardMarkup:
    keyboard = [
        [
            KeyboardButton(text=BOOK_ROOM_TEXT),
            KeyboardButton(text=MY_RESERVATIONS_TEXT),
        ],
        [
            KeyboardButton(text=SCHEDULE_TEXT),
            KeyboardButton(text=HELP_TEXT),
        ],
    ]

    if is_admin:
        keyboard.extend(
            [
                [
                    KeyboardButton(text=ALL_RESERVATIONS_TEXT),
                    KeyboardButton(text=ROOMS_MANAGEMENT_TEXT),
                ],
                [
                    KeyboardButton(text=ANALYTICS_TEXT),
                    KeyboardButton(text=USERS_MANAGEMENT_TEXT),
                ],
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
        input_field_placeholder="Можно отменить регистрацию",
    )


async def send_main_menu(message: Message, *, full_name: str, is_admin: bool) -> None:
    role_text = "Администратор" if is_admin else "Сотрудник"
    await message.answer(
        (
            f"Привет, {full_name}!\n\n"
            f"Твоя роль: {role_text}.\n"
            "Выбери действие в меню."
        ),
        reply_markup=main_menu_keyboard(is_admin=is_admin),
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
        (
            "Давай зарегистрируем тебя в системе бронирования.\n\n"
            "Введите ФИО полностью, например: Иванов Иван Иванович."
        ),
        reply_markup=cancel_keyboard(),
    )


@router.message(Command("cancel"))
@router.message(F.text == CANCEL_TEXT)
async def cancel_registration(message: Message, state: FSMContext) -> None:
    current_state = await state.get_state()
    await state.clear()

    if current_state:
        await message.answer(
            "Регистрация отменена. Чтобы начать заново, отправьте /start.",
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
async def process_email(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
) -> None:
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
    await message.answer(
        "Регистрация завершена.",
        reply_markup=ReplyKeyboardRemove(),
    )
    await send_main_menu(message, full_name=user.full_name, is_admin=user.is_admin)


@router.message(F.text == HELP_TEXT)
async def help_message(message: Message) -> None:
    await message.answer(
        "Бот подключен к базе данных. Сейчас доступна регистрация через /start; дальше добавим комнаты и бронирования."
    )


@router.message(F.text.in_({BOOK_ROOM_TEXT, MY_RESERVATIONS_TEXT, SCHEDULE_TEXT}))
async def feature_stub(message: Message) -> None:
    await message.answer(
        "Этот сценарий уже есть в меню. Следующим шагом реализуем работу с комнатами и бронированиями."
    )


@router.message(
    F.text.in_(
        {
            ALL_RESERVATIONS_TEXT,
            ROOMS_MANAGEMENT_TEXT,
            ANALYTICS_TEXT,
            USERS_MANAGEMENT_TEXT,
        }
    )
)
async def admin_feature_stub(message: Message) -> None:
    await message.answer("Административный сценарий добавим на следующих этапах.")


@router.message()
async def unknown_message(message: Message) -> None:
    await message.answer("Не понял команду. Выберите действие в меню или отправьте /start.")
