from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Reservation, Room
from app.repositories.reservations import list_reservations_for_period
from app.repositories.rooms import list_rooms

LOCAL_TIMEZONE = timezone(timedelta(hours=5), name="Asia/Yekaterinburg")


@dataclass(frozen=True)
class RoomSchedule:
    room: Room
    reservations: list[Reservation]


def parse_schedule_date(value: str) -> date:
    normalized_value = value.strip().lower()

    if normalized_value in {"сегодня", "today"}:
        return datetime.now(LOCAL_TIMEZONE).date()
    if normalized_value in {"завтра", "tomorrow"}:
        from datetime import timedelta

        return datetime.now(LOCAL_TIMEZONE).date() + timedelta(days=1)

    for date_format in ("%d.%m.%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(normalized_value, date_format).date()
        except ValueError:
            continue

    raise ValueError("Введите дату в формате ДД.ММ.ГГГГ, например 26.04.2026.")


def get_day_bounds(schedule_date: date) -> tuple[datetime, datetime]:
    start_at = datetime.combine(schedule_date, time.min, tzinfo=LOCAL_TIMEZONE)
    end_at = datetime.combine(schedule_date, time.max, tzinfo=LOCAL_TIMEZONE)
    return start_at, end_at


async def get_schedule_for_date(
    session: AsyncSession,
    *,
    schedule_date: date,
) -> list[RoomSchedule]:
    day_start, day_end = get_day_bounds(schedule_date)
    rooms = [room for room in await list_rooms(session) if room.is_active]
    reservations = await list_reservations_for_period(
        session,
        start_at=day_start,
        end_at=day_end,
    )

    reservations_by_room_id: dict[int, list[Reservation]] = {
        room.room_id: [] for room in rooms
    }
    for reservation in reservations:
        if reservation.room_id in reservations_by_room_id:
            reservations_by_room_id[reservation.room_id].append(reservation)

    return [
        RoomSchedule(room=room, reservations=reservations_by_room_id[room.room_id])
        for room in rooms
    ]


def format_schedule(schedule_date: date, schedule: list[RoomSchedule]) -> str:
    formatted_date = schedule_date.strftime("%d.%m.%Y")
    if not schedule:
        return f"Расписание на {formatted_date}\n\nАктивные комнаты пока не добавлены."

    lines = [f"Расписание на {formatted_date}"]

    for item in schedule:
        lines.append(
            f"\n#{item.room.room_id} {item.room.name} "
            f"({item.room.location}, мест: {item.room.capacity})"
        )
        if not item.reservations:
            lines.append("Свободна весь день.")
            continue

        for reservation in item.reservations:
            start_time = reservation.start_datetime.astimezone(LOCAL_TIMEZONE).strftime("%H:%M")
            end_time = reservation.end_datetime.astimezone(LOCAL_TIMEZONE).strftime("%H:%M")
            lines.append(
                f"{start_time}-{end_time}: {reservation.purpose} "
                f"({reservation.status.name})"
            )

    return "\n".join(lines)
