import asyncio
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.db.models import User
from app.db.session import async_session_factory, engine
from app.services.users import get_users, set_user_admin_status


async def main() -> None:
    async with async_session_factory() as session:
        async with session.begin():
            admin = User(
                full_name="Администратор Тест",
                email="user-management-admin@example.com",
                telegram_id=999999999701,
                is_admin=True,
            )
            employee = User(
                full_name="Сотрудник Тест",
                email="user-management-employee@example.com",
                telegram_id=999999999702,
                is_admin=False,
            )
            session.add_all([admin, employee])
            await session.flush()

            users = await get_users(session)
            assert any(user.user_id == admin.user_id for user in users)
            assert any(user.user_id == employee.user_id for user in users)

            updated_employee = await set_user_admin_status(
                session,
                user_id=employee.user_id,
                is_admin=True,
            )
            assert updated_employee.is_admin is True

            updated_employee = await set_user_admin_status(
                session,
                user_id=employee.user_id,
                is_admin=False,
            )
            assert updated_employee.is_admin is False

            try:
                await set_user_admin_status(session, user_id=999999999, is_admin=True)
            except ValueError:
                missing_user_blocked = True
            else:
                missing_user_blocked = False
            assert missing_user_blocked

            await session.rollback()

    await engine.dispose()
    print("USER_MANAGEMENT_OK")


if __name__ == "__main__":
    asyncio.run(main())
