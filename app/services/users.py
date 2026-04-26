from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User
from app.repositories.users import add_user, get_user_by_telegram_id


def build_placeholder_email(telegram_id: int) -> str:
    return f"telegram_{telegram_id}@telegram.local"


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
