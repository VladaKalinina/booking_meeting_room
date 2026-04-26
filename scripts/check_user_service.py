import asyncio
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.db.session import async_session_factory, engine
from app.services.users import get_or_create_user_from_telegram


async def main() -> None:
    async with async_session_factory() as session:
        async with session.begin():
            user, created = await get_or_create_user_from_telegram(
                session,
                telegram_id=999999999001,
                full_name="Test Telegram User",
            )
            print(
                "USER_SERVICE_OK "
                f"user_id={user.user_id} telegram_id={user.telegram_id} created={created}"
            )
            await session.rollback()

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
