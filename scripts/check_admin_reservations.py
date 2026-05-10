import asyncio
import sys
from datetime import datetime, time, timedelta
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.db.models import User
from app.db.session import async_session_factory, engine
from app.services.bookings import (
    BookingDraft,
    cancel_any_reservation,
    create_booking,
    get_all_reservations,
)
from app.services.rooms import create_room
from app.services.schedule import LOCAL_TIMEZONE


async def main() -> None:
    async with async_session_factory() as session:
        async with session.begin():
            organizer = User(
                full_name="Админ Список Организатор",
                email="admin-reservations-organizer@example.com",
                telegram_id=999999999601,
            )
            session.add(organizer)
            await session.flush()

            room = await create_room(
                session,
                name="Админ бронирования тест",
                location="6 этаж",
                capacity=5,
            )
            booking_date = datetime.now(LOCAL_TIMEZONE).date() + timedelta(days=3)
            reservation = await create_booking(
                session,
                organizer=organizer,
                room_id=room.room_id,
                draft=BookingDraft(
                    start_at=datetime.combine(booking_date, time(14, 0), tzinfo=LOCAL_TIMEZONE),
                    end_at=datetime.combine(booking_date, time(15, 0), tzinfo=LOCAL_TIMEZONE),
                    purpose="Админская проверка",
                    capacity=3,
                    equipment_type_ids=[],
                ),
            )

            all_reservations = await get_all_reservations(session)
            assert any(item.reservation_id == reservation.reservation_id for item in all_reservations)

            canceled = await cancel_any_reservation(
                session,
                reservation_id=reservation.reservation_id,
            )
            assert canceled.status_id == 3

            try:
                await cancel_any_reservation(
                    session,
                    reservation_id=reservation.reservation_id,
                )
            except ValueError:
                repeat_cancel_blocked = True
            else:
                repeat_cancel_blocked = False
            assert repeat_cancel_blocked

            await session.rollback()

    await engine.dispose()
    print("ADMIN_RESERVATIONS_OK")


if __name__ == "__main__":
    asyncio.run(main())
