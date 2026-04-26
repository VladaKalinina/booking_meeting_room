import re

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User
from app.repositories.users import add_user, get_user_by_email, get_user_by_telegram_id

EMAIL_PATTERN = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")


def build_placeholder_email(telegram_id: int) -> str:
    return f"telegram_{telegram_id}@telegram.local"


def is_placeholder_email(email: str) -> bool:
    return email.endswith("@telegram.local")


def normalize_email(email: str) -> str:
    return email.strip().lower()


def is_valid_email(email: str) -> bool:
    return EMAIL_PATTERN.fullmatch(normalize_email(email)) is not None


def is_profile_complete(user: User) -> bool:
    return bool(user.full_name.strip()) and not is_placeholder_email(user.email)


async def get_or_create_user_from_telegram(
    session: AsyncSession,
    *,
    telegram_id: int,
    full_name: str,
) -> tuple[User, bool]:
    user = await get_user_by_telegram_id(session, telegram_id)
    if user:
        if user.full_name != full_name:
            user.full_name = full_name
            await session.flush()
        return user, False

    user = await add_user(
        session,
        telegram_id=telegram_id,
        full_name=full_name,
        email=build_placeholder_email(telegram_id),
    )
    return user, True


async def register_or_update_user_profile(
    session: AsyncSession,
    *,
    telegram_id: int,
    full_name: str,
    email: str,
) -> tuple[User, bool]:
    normalized_full_name = " ".join(full_name.split())
    normalized_email = normalize_email(email)

    if not normalized_full_name:
        raise ValueError("ФИО не может быть пустым.")
    if not is_valid_email(normalized_email):
        raise ValueError("Введите корректный email.")

    existing_email_user = await get_user_by_email(session, normalized_email)
    if existing_email_user and existing_email_user.telegram_id != telegram_id:
        raise ValueError("Этот email уже используется другим пользователем.")

    user = await get_user_by_telegram_id(session, telegram_id)
    created = False

    if not user:
        user = await add_user(
            session,
            telegram_id=telegram_id,
            full_name=normalized_full_name,
            email=normalized_email,
        )
        created = True
    else:
        user.full_name = normalized_full_name
        user.email = normalized_email
        await session.flush()

    return user, created
