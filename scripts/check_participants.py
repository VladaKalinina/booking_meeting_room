import asyncio
import sys
from datetime import datetime, time, timedelta
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.db.models import User
from app.db.session import async_session_factory, engine
from app.services.bookings import BookingDraft, create_booking
from app.services.participants import (
    ACCEPTED_INVITATION_STATUS_ID,
    add_participants_by_email,
    format_participants,
    list_reservation_participants,
    parse_participant_emails,
    set_invitation_status,
)
from app.services.rooms import create_room
from app.services.schedule import LOCAL_TIMEZONE


async def main() -> None:
    async with async_session_factory() as session:
        async with session.begin():
            organizer = User(
                full_name="Participants Organizer",
                email="participants-organizer@example.com",
                telegram_id=999999999901,
            )
            invited = User(
                full_name="Participants Invited",
                email="participants-invited@example.com",
                telegram_id=999999999902,
            )
            session.add_all([organizer, invited])
            await session.flush()

            room = await create_room(
                session,
                name="Participants Room",
                location="9 floor",
                capacity=6,
            )
            booking_date = datetime.now(LOCAL_TIMEZONE).date() + timedelta(days=1)
            reservation = await create_booking(
                session,
                organizer=organizer,
                room_id=room.room_id,
                draft=BookingDraft(
                    start_at=datetime.combine(booking_date, time(14, 0), tzinfo=LOCAL_TIMEZONE),
                    end_at=datetime.combine(booking_date, time(15, 0), tzinfo=LOCAL_TIMEZONE),
                    purpose="Participants check",
                    capacity=4,
                    equipment_type_ids=[],
                ),
            )

            emails = parse_participant_emails(
                "participants-invited@example.com, missing@example.com"
            )
            result = await add_participants_by_email(
                session,
                organizer=organizer,
                reservation_id=reservation.reservation_id,
                emails=emails,
            )
            assert len(result.added) == 1
            assert result.not_found_emails == ["missing@example.com"]

            participant = result.added[0]
            updated = await set_invitation_status(
                session,
                participant_id=participant.participant_id,
                telegram_id=invited.telegram_id,
                status_id=ACCEPTED_INVITATION_STATUS_ID,
            )
            assert updated.invitation_status_id == ACCEPTED_INVITATION_STATUS_ID

            participants = await list_reservation_participants(
                session,
                reservation_id=reservation.reservation_id,
            )
            assert "Participants Invited" in format_participants(participants)

            await session.rollback()

    await engine.dispose()
    print("PARTICIPANTS_OK")


if __name__ == "__main__":
    asyncio.run(main())
