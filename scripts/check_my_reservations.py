import asyncio
import sys
from datetime import datetime
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.db.models import User
from app.db.session import async_session_factory, engine
from app.services.bookings import (
    BookingDraft,
    cancel_own_reservation,
    create_booking,
    get_my_active_reservations,
)
from app.services.rooms import create_room
from app.services.schedule import LOCAL_TIMEZONE


async def main() -> None:
    async with async_session_factory() as session:
        async with session.begin():
            organizer = User(
                full_name="Организатор Тест",
                email="my-reservations-organizer@example.com",
                telegram_id=999999999501,
            )
            stranger = User(
                full_name="Чужой Пользователь",
                email="my-reservations-stranger@example.com",
                telegram_id=999999999502,
            )
            session.add_all([organizer, stranger])
            await session.flush()

            room = await create_room(
                session,
                name="Мои бронирования тест",
                location="5 этаж",
                capacity=4,
            )
            draft = BookingDraft(
                start_at=datetime(2026, 4, 28, 12, 0, tzinfo=LOCAL_TIMEZONE),
                end_at=datetime(2026, 4, 28, 13, 0, tzinfo=LOCAL_TIMEZONE),
                purpose="Проверка списка",
                capacity=2,
                equipment_type_ids=[],
            )
            reservation = await create_booking(
                session,
                organizer=organizer,
                room_id=room.room_id,
                draft=draft,
            )

            active_reservations = await get_my_active_reservations(
                session,
                organizer=organizer,
            )
            assert any(item.reservation_id == reservation.reservation_id for item in active_reservations)

            try:
                await cancel_own_reservation(
                    session,
                    organizer=stranger,
                    reservation_id=reservation.reservation_id,
                )
            except ValueError:
                stranger_blocked = True
            else:
                stranger_blocked = False
            assert stranger_blocked

            await cancel_own_reservation(
                session,
                organizer=organizer,
                reservation_id=reservation.reservation_id,
            )
            active_after_cancel = await get_my_active_reservations(
                session,
                organizer=organizer,
            )
            assert all(item.reservation_id != reservation.reservation_id for item in active_after_cancel)

            await session.rollback()

    await engine.dispose()
    print("MY_RESERVATIONS_OK")


if __name__ == "__main__":
    asyncio.run(main())
