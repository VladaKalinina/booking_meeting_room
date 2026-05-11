import asyncio
import sys
from datetime import datetime, time, timedelta
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.db.models import User
from app.db.session import async_session_factory, engine
from app.services.bookings import BookingDraft, create_booking, update_booking
from app.services.rooms import create_room
from app.services.schedule import LOCAL_TIMEZONE


async def main() -> None:
    async with async_session_factory() as session:
        async with session.begin():
            organizer = User(
                full_name="Booking Edit Organizer",
                email="booking-edit-organizer@example.com",
                telegram_id=999999999801,
            )
            session.add(organizer)
            await session.flush()

            first_room = await create_room(
                session,
                name="Booking Edit First Room",
                location="8 floor",
                capacity=4,
            )
            second_room = await create_room(
                session,
                name="Booking Edit Second Room",
                location="8 floor",
                capacity=8,
            )

            booking_date = datetime.now(LOCAL_TIMEZONE).date() + timedelta(days=1)
            reservation = await create_booking(
                session,
                organizer=organizer,
                room_id=first_room.room_id,
                draft=BookingDraft(
                    start_at=datetime.combine(booking_date, time(10, 0), tzinfo=LOCAL_TIMEZONE),
                    end_at=datetime.combine(booking_date, time(11, 0), tzinfo=LOCAL_TIMEZONE),
                    purpose="Initial purpose",
                    capacity=3,
                    equipment_type_ids=[],
                ),
            )

            updated = await update_booking(
                session,
                organizer=organizer,
                reservation_id=reservation.reservation_id,
                room_id=second_room.room_id,
                draft=BookingDraft(
                    start_at=datetime.combine(booking_date, time(12, 0), tzinfo=LOCAL_TIMEZONE),
                    end_at=datetime.combine(booking_date, time(13, 0), tzinfo=LOCAL_TIMEZONE),
                    purpose="Updated purpose",
                    capacity=6,
                    equipment_type_ids=[],
                ),
            )

            assert updated.room_id == second_room.room_id
            assert updated.purpose == "Updated purpose"
            assert updated.start_datetime.hour == 12

            await session.rollback()

    await engine.dispose()
    print("BOOKING_EDIT_OK")


if __name__ == "__main__":
    asyncio.run(main())
