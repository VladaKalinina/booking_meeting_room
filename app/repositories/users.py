from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User


async def get_user_by_telegram_id(
    session: AsyncSession,
    telegram_id: int,
) -> User | None:
    result = await session.execute(
        select(User).where(User.telegram_id == telegram_id)
    )
    return result.scalar_one_or_none()


async def add_user(
    session: AsyncSession,
    *,
    telegram_id: int,
    full_name: str,
    email: str,
) -> User:
    user = User(
        telegram_id=telegram_id,
        full_name=full_name,
        email=email,
    )
    session.add(user)
    await session.flush()
    return user
