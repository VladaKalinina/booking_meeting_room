import asyncio
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.db.session import async_session_factory, engine
from app.services.users import (
    is_profile_complete,
    is_valid_email,
    register_or_update_user_profile,
)


async def main() -> None:
    async with async_session_factory() as session:
        async with session.begin():
            user, created = await register_or_update_user_profile(
                session,
                telegram_id=999999999101,
                full_name="Иванов Иван",
                email="Ivanov.Test@example.com",
            )

            assert created is True
            assert user.email == "ivanov.test@example.com"
            assert is_profile_complete(user)
            assert is_valid_email(user.email)

            same_user, created_again = await register_or_update_user_profile(
                session,
                telegram_id=999999999101,
                full_name="Иванов Иван Петрович",
                email="ivanov.test@example.com",
            )

            assert created_again is False
            assert same_user.user_id == user.user_id
            assert same_user.full_name == "Иванов Иван Петрович"

            try:
                await register_or_update_user_profile(
                    session,
                    telegram_id=999999999102,
                    full_name="Петров Петр",
                    email="ivanov.test@example.com",
                )
            except ValueError:
                duplicate_email_blocked = True
            else:
                duplicate_email_blocked = False

            assert duplicate_email_blocked
            await session.rollback()

    await engine.dispose()
    print("REGISTRATION_OK")


if __name__ == "__main__":
    asyncio.run(main())
