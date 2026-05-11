import asyncio
import sys
from datetime import datetime, time, timedelta
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.db.models import User
from app.db.session import async_session_factory, engine
from app.services.analytics import format_admin_analytics, get_admin_analytics
from app.services.bookings import (
    BookingDraft,
    cancel_any_reservation,
    create_booking,
)
from app.services.rooms import create_room, deactivate_room
from app.services.schedule import LOCAL_TIMEZONE


async def main() -> None:
    async with async_session_factory() as session:
        async with session.begin():
            admin = User(
                full_name="Analytics Admin",
                email="analytics-admin@example.com",
                telegram_id=999999999701,
                is_admin=True,
            )
            user = User(
                full_name="Analytics User",
                email="analytics-user@example.com",
                telegram_id=999999999702,
            )
            session.add_all([admin, user])
            await session.flush()

            active_room = await create_room(
                session,
                name="Analytics Room",
                location="7 floor",
                capacity=8,
            )
            inactive_room = await create_room(
                session,
                name="Analytics Inactive Room",
                location="7 floor",
                capacity=4,
            )
            await deactivate_room(session, inactive_room.room_id)

            booking_date = datetime.now(LOCAL_TIMEZONE).date() + timedelta(days=1)
            reservation = await create_booking(
                session,
                organizer=user,
                room_id=active_room.room_id,
                draft=BookingDraft(
                    start_at=datetime.combine(booking_date, time(10, 0), tzinfo=LOCAL_TIMEZONE),
                    end_at=datetime.combine(booking_date, time(11, 0), tzinfo=LOCAL_TIMEZONE),
                    purpose="Analytics active booking",
                    capacity=4,
                    equipment_type_ids=[],
                ),
            )
            canceled = await create_booking(
                session,
                organizer=user,
                room_id=active_room.room_id,
                draft=BookingDraft(
                    start_at=datetime.combine(booking_date, time(12, 0), tzinfo=LOCAL_TIMEZONE),
                    end_at=datetime.combine(booking_date, time(13, 0), tzinfo=LOCAL_TIMEZONE),
                    purpose="Analytics canceled booking",
                    capacity=4,
                    equipment_type_ids=[],
                ),
            )
            await cancel_any_reservation(session, reservation_id=canceled.reservation_id)

            analytics = await get_admin_analytics(session)
            report = format_admin_analytics(analytics)

            assert analytics.users_count >= 2
            assert analytics.admins_count >= 1
            assert analytics.rooms_count >= 2
            assert analytics.active_rooms_count >= 1
            assert analytics.reservations_count >= 2
            assert analytics.active_reservations_count >= 1
            assert analytics.canceled_reservations_count >= 1
            assert analytics.created_last_30_days_count >= 2
            assert analytics.upcoming_7_days_count >= 1
            assert reservation.reservation_id is not None
            assert "Аналитика бронирований" in report

            await session.rollback()

    await engine.dispose()
    print("ANALYTICS_OK")


if __name__ == "__main__":
    asyncio.run(main())
