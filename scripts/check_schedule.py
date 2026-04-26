import asyncio
import sys
from datetime import date, datetime
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.db.models import Reservation, User
from app.db.session import async_session_factory, engine
from app.services.rooms import create_room
from app.services.schedule import (
    LOCAL_TIMEZONE,
    format_schedule,
    get_schedule_for_date,
    parse_schedule_date,
)


async def main() -> None:
    async with async_session_factory() as session:
        async with session.begin():
            user = User(
                full_name="Тестовый Организатор",
                email="schedule-test@example.com",
                telegram_id=999999999301,
            )
            session.add(user)
            await session.flush()

            room = await create_room(
                session,
                name="Расписание тест",
                location="1 этаж",
                capacity=6,
            )
            reservation_date = date(2026, 4, 26)
            reservation = Reservation(
                organizer_id=user.user_id,
                room_id=room.room_id,
                status_id=1,
                start_datetime=datetime(2026, 4, 26, 10, 0, tzinfo=LOCAL_TIMEZONE),
                end_datetime=datetime(2026, 4, 26, 11, 0, tzinfo=LOCAL_TIMEZONE),
                purpose="Тестовая встреча",
            )
            session.add(reservation)
            await session.flush()

            assert parse_schedule_date("26.04.2026") == reservation_date
            assert parse_schedule_date("2026-04-26") == reservation_date

            schedule = await get_schedule_for_date(session, schedule_date=reservation_date)
            formatted_schedule = format_schedule(reservation_date, schedule)

            assert "Расписание тест" in formatted_schedule
            assert "10:00-11:00" in formatted_schedule
            assert "Тестовая встреча" in formatted_schedule

            await session.rollback()

    await engine.dispose()
    print("SCHEDULE_OK")


if __name__ == "__main__":
    asyncio.run(main())
