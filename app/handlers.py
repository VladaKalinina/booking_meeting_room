from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.types import KeyboardButton, Message, ReplyKeyboardMarkup
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.users import get_or_create_user_from_telegram

router = Router()

BOOK_ROOM_TEXT = "Забронировать"
MY_RESERVATIONS_TEXT = "Мои бронирования"
SCHEDULE_TEXT = "Расписание"
HELP_TEXT = "Помощь"


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text=BOOK_ROOM_TEXT),
                KeyboardButton(text=MY_RESERVATIONS_TEXT),
            ],
            [
                KeyboardButton(text=SCHEDULE_TEXT),
                KeyboardButton(text=HELP_TEXT),
            ],
        ],
        resize_keyboard=True,
        input_field_placeholder="Выберите действие",
    )


@router.message(CommandStart())
async def start(message: Message, session: AsyncSession) -> None:
    if not message.from_user:
        await message.answer("Не удалось определить пользователя Telegram.")
        return

    user, created = await get_or_create_user_from_telegram(
        session,
        telegram_id=message.from_user.id,
        full_name=message.from_user.full_name,
    )
    await session.commit()

    status_text = "Я зарегистрировал тебя в системе." if created else "Ты уже есть в системе."
    role_text = "Администратор" if user.is_admin else "Сотрудник"

    await message.answer(
        (
            f"Привет, {user.full_name}!\n\n"
            f"{status_text}\n"
            f"Твоя роль: {role_text}.\n\n"
            "Теперь можно подключать сценарии бронирования переговорных комнат."
        ),
        reply_markup=main_menu_keyboard(),
    )


@router.message(F.text == HELP_TEXT)
async def help_message(message: Message) -> None:
    await message.answer(
        "Бот уже подключен к базе данных. Сейчас доступна регистрация через /start, дальше добавим комнаты и бронирования."
    )


@router.message(F.text.in_({BOOK_ROOM_TEXT, MY_RESERVATIONS_TEXT, SCHEDULE_TEXT}))
async def feature_stub(message: Message) -> None:
    await message.answer(
        "Этот сценарий уже есть в меню. Следующим шагом реализуем работу с комнатами и бронированиями."
    )


@router.message()
async def unknown_message(message: Message) -> None:
    await message.answer("Не понял команду. Выберите действие в меню или отправьте /start.")
