import asyncio
import sys
from pathlib import Path

from sqlalchemy import text

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.db.session import async_session_factory, engine


async def main() -> None:
    async with async_session_factory() as session:
        result = await session.execute(
            text(
                """
                select user_id, full_name, email, telegram_id, is_admin, registered_at
                from users
                order by user_id
                """
            )
        )
        for row in result:
            print(
                f"{row.user_id}: {row.full_name!r}, "
                f"telegram_id={row.telegram_id}, email={row.email}, is_admin={row.is_admin}"
            )

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
