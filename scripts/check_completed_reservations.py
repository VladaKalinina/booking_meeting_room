import asyncio
import sys
from datetime import datetime, time, timedelta
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.db.models import Reservation, User
from app.db.session import async_session_factory, engine
from app.services.bookings import (
    COMPLETED_STATUS_ID,
    complete_finished_reservations,
    get_all_reservations,
    get_my_active_reservations,
)
from app.services.rooms import create_room
from app.services.schedule import LOCAL_TIMEZONE


async def main() -> None:
    async with async_session_factory() as session:
        async with session.begin():
            organizer = User(
                full_name="Completed Reservation Organizer",
                email="completed-reservation-organizer@example.com",
                telegram_id=999999999951,
            )
            session.add(organizer)
            await session.flush()

            room = await create_room(
                session,
                name="Completed Reservation Room",
                location="10 floor",
                capacity=4,
            )

            reservation_date = datetime.now(LOCAL_TIMEZONE).date() - timedelta(days=1)
            reservation = Reservation(
                organizer_id=organizer.user_id,
                room_id=room.room_id,
                status_id=1,
                start_datetime=datetime.combine(
                    reservation_date,
                    time(10, 0),
                    tzinfo=LOCAL_TIMEZONE,
                ),
                end_datetime=datetime.combine(
                    reservation_date,
                    time(11, 0),
                    tzinfo=LOCAL_TIMEZONE,
                ),
                purpose="Completed reservation check",
            )
            session.add(reservation)
            await session.flush()

            completed_count = await complete_finished_reservations(session)
            assert completed_count >= 1

            active_reservations = await get_my_active_reservations(
                session,
                organizer=organizer,
            )
            assert all(
                item.reservation_id != reservation.reservation_id
                for item in active_reservations
            )

            all_reservations = await get_all_reservations(session)
            completed_reservation = next(
                item
                for item in all_reservations
                if item.reservation_id == reservation.reservation_id
            )
            assert completed_reservation.status_id == COMPLETED_STATUS_ID

            await session.rollback()

    await engine.dispose()
    print("COMPLETED_RESERVATIONS_OK")


if __name__ == "__main__":
    asyncio.run(main())
