import asyncio
import sys
from datetime import date, datetime
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.db.models import User
from app.db.session import async_session_factory, engine
from app.services.bookings import (
    BookingDraft,
    create_booking,
    get_available_rooms,
    parse_equipment_type_ids,
    parse_time,
)
from app.services.equipment import (
    attach_equipment_to_room,
    create_equipment,
    create_equipment_type,
)
from app.services.rooms import create_room
from app.services.schedule import LOCAL_TIMEZONE


async def main() -> None:
    async with async_session_factory() as session:
        async with session.begin():
            user = User(
                full_name="Тестовый Бронирующий",
                email="booking-test@example.com",
                telegram_id=999999999401,
            )
            session.add(user)
            await session.flush()

            room = await create_room(
                session,
                name="Бронирование тест",
                location="4 этаж",
                capacity=10,
            )
            equipment_type = await create_equipment_type(session, name="Экран")
            equipment = await create_equipment(
                session,
                type_id=equipment_type.type_id,
                part_number="SCREEN-TEST-001",
            )
            await attach_equipment_to_room(
                session,
                room_id=room.room_id,
                equipment_id=equipment.equipment_id,
            )

            booking_date = date(2026, 4, 27)
            draft = BookingDraft(
                start_at=datetime(2026, 4, 27, 10, 0, tzinfo=LOCAL_TIMEZONE),
                end_at=datetime(2026, 4, 27, 11, 0, tzinfo=LOCAL_TIMEZONE),
                purpose="Планирование",
                capacity=6,
                equipment_type_ids=parse_equipment_type_ids(str(equipment_type.type_id)),
            )

            assert parse_time("10:00").hour == 10
            available_rooms = await get_available_rooms(
                session,
                start_at=draft.start_at,
                end_at=draft.end_at,
                capacity=draft.capacity,
                equipment_type_ids=draft.equipment_type_ids,
            )
            assert any(item.room_id == room.room_id for item in available_rooms)

            reservation = await create_booking(
                session,
                organizer=user,
                room_id=room.room_id,
                draft=draft,
            )
            assert reservation.reservation_id is not None

            unavailable_rooms = await get_available_rooms(
                session,
                start_at=draft.start_at,
                end_at=draft.end_at,
                capacity=draft.capacity,
                equipment_type_ids=draft.equipment_type_ids,
            )
            assert all(item.room_id != room.room_id for item in unavailable_rooms)

            assert booking_date == draft.start_at.date()
            await session.rollback()

    await engine.dispose()
    print("BOOKING_OK")


if __name__ == "__main__":
    asyncio.run(main())
