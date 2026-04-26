import asyncio
import sys
from pathlib import Path

from sqlalchemy import select

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.db.models import User
from app.db.session import async_session_factory, engine


def print_usage() -> None:
    print("Usage:")
    print("  python scripts/set_admin.py <telegram_id_or_email> true")
    print("  python scripts/set_admin.py <telegram_id_or_email> false")


async def main() -> None:
    if len(sys.argv) != 3 or sys.argv[2].lower() not in {"true", "false"}:
        print_usage()
        raise SystemExit(1)

    lookup_value = sys.argv[1]
    is_admin = sys.argv[2].lower() == "true"

    async with async_session_factory() as session:
        if lookup_value.isdigit():
            query = select(User).where(User.telegram_id == int(lookup_value))
        else:
            query = select(User).where(User.email == lookup_value.lower())

        result = await session.execute(query)
        user = result.scalar_one_or_none()

        if not user:
            print("USER_NOT_FOUND")
            raise SystemExit(1)

        user.is_admin = is_admin
        await session.commit()

        role = "admin" if user.is_admin else "employee"
        print(f"USER_ROLE_UPDATED user_id={user.user_id} role={role}")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
