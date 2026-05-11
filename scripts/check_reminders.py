import asyncio
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.db.models import Reservation, Room
from app.services.reminders import format_reservation_reminder, reservation_should_be_reminded
from app.services.schedule import LOCAL_TIMEZONE


async def main() -> None:
    now = datetime.now(LOCAL_TIMEZONE)
    reservation = Reservation(
        reservation_id=1,
        organizer_id=1,
        room_id=1,
        status_id=1,
        start_datetime=now + timedelta(minutes=15, seconds=20),
        end_datetime=now + timedelta(minutes=45),
        purpose="Reminder check",
    )
    reservation.room = Room(
        room_id=1,
        name="Reminder Room",
        location="Reminder Location",
        capacity=4,
    )

    assert reservation_should_be_reminded(reservation, now)
    assert "Reminder check" in format_reservation_reminder(reservation)

    print("REMINDERS_OK")


if __name__ == "__main__":
    asyncio.run(main())
