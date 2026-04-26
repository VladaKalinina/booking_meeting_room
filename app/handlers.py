from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.types import KeyboardButton, Message, ReplyKeyboardMarkup

router = Router()


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="Забронировать"),
                KeyboardButton(text="Мои бронирования"),
            ],
            [
                KeyboardButton(text="Расписание"),
                KeyboardButton(text="Помощь"),
            ],
        ],
        resize_keyboard=True,
        input_field_placeholder="Выберите действие",
    )


@router.message(CommandStart())
async def start(message: Message) -> None:
    user_name = message.from_user.full_name if message.from_user else "коллега"
    await message.answer(
        (
            f"Привет, {user_name}!\n\n"
            "Я бот для бронирования переговорных комнат. "
            "Пока я запущен в минимальном режиме: проверяем, что Telegram-часть работает."
        ),
        reply_markup=main_menu_keyboard(),
    )


@router.message(F.text == "Помощь")
async def help_message(message: Message) -> None:
    await message.answer(
        "Сейчас доступна проверка запуска бота. Следующим шагом подключим базу данных и начнем хранить комнаты и бронирования."
    )


@router.message(F.text.in_({"Забронировать", "Мои бронирования", "Расписание"}))
async def feature_stub(message: Message) -> None:
    await message.answer(
        "Этот сценарий уже есть в меню. Реализуем его после подключения базы данных."
    )


@router.message()
async def unknown_message(message: Message) -> None:
    await message.answer("Не понял команду. Выберите действие в меню или отправьте /start.")
