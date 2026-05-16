import asyncio
import sys
from datetime import datetime, time, timedelta
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.db.models import User
from app.db.session import async_session_factory, engine
from app.services.bookings import BookingDraft, create_booking
from app.services.calendar_invites import (
    build_google_calendar_url,
    build_outlook_calendar_url,
    build_reservation_ics,
    reservation_ics_filename,
)
from app.services.rooms import create_room
from app.services.schedule import LOCAL_TIMEZONE


async def main() -> None:
    async with async_session_factory() as session:
        async with session.begin():
            user = User(
                full_name="Calendar Invite Organizer",
                email="calendar-invite-organizer@example.com",
                telegram_id=999999999961,
            )
            session.add(user)
            await session.flush()

            room = await create_room(
                session,
                name="Calendar Room",
                location="11 floor",
                capacity=6,
            )
            booking_date = datetime.now(LOCAL_TIMEZONE).date() + timedelta(days=1)
            reservation = await create_booking(
                session,
                organizer=user,
                room_id=room.room_id,
                draft=BookingDraft(
                    start_at=datetime.combine(booking_date, time(16, 0), tzinfo=LOCAL_TIMEZONE),
                    end_at=datetime.combine(booking_date, time(17, 0), tzinfo=LOCAL_TIMEZONE),
                    purpose="Calendar planning",
                    capacity=4,
                    equipment_type_ids=[],
                ),
            )

            ics_text = build_reservation_ics(reservation).decode("utf-8")

            assert reservation_ics_filename(reservation).endswith(".ics")
            assert "BEGIN:VCALENDAR" in ics_text
            assert "BEGIN:VEVENT" in ics_text
            assert "BEGIN:VTIMEZONE" in ics_text
            assert "TZID:Asia/Yekaterinburg" in ics_text
            assert "DTSTART;TZID=Asia/Yekaterinburg:" in ics_text
            assert "DTEND;TZID=Asia/Yekaterinburg:" in ics_text
            assert "STATUS:CONFIRMED" in ics_text
            assert "\r\n" in ics_text
            assert "Calendar Room" in ics_text
            assert "Calendar planning" in ics_text
            assert build_google_calendar_url(reservation).startswith(
                "https://calendar.google.com/calendar/render?"
            )
            assert build_outlook_calendar_url(reservation).startswith(
                "https://outlook.live.com/calendar/0/deeplink/compose?"
            )

            await session.rollback()

    await engine.dispose()
    print("CALENDAR_INVITE_OK")


if __name__ == "__main__":
    asyncio.run(main())
