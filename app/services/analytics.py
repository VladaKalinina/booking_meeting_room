from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.reservations import ACTIVE_RESERVATION_STATUS_IDS
from app.services.bookings import CANCELED_STATUS_ID, get_all_reservations
from app.services.rooms import get_rooms
from app.services.schedule import LOCAL_TIMEZONE
from app.services.users import get_users


@dataclass(frozen=True)
class RoomUsage:
    room_id: int
    room_name: str
    reservations_count: int
    hours_count: float


@dataclass(frozen=True)
class AdminAnalytics:
    users_count: int
    admins_count: int
    rooms_count: int
    active_rooms_count: int
    reservations_count: int
    active_reservations_count: int
    canceled_reservations_count: int
    created_last_30_days_count: int
    upcoming_7_days_count: int
    top_rooms: list[RoomUsage]


async def get_admin_analytics(session: AsyncSession) -> AdminAnalytics:
    users = await get_users(session)
    rooms = await get_rooms(session)
    reservations = await get_all_reservations(session)

    now = datetime.now(LOCAL_TIMEZONE)
    last_30_days_start = now - timedelta(days=30)
    next_7_days_end = now + timedelta(days=7)

    active_reservations = [
        reservation
        for reservation in reservations
        if reservation.status_id in ACTIVE_RESERVATION_STATUS_IDS
    ]
    canceled_reservations = [
        reservation
        for reservation in reservations
        if reservation.status_id == CANCELED_STATUS_ID
    ]
    created_last_30_days = [
        reservation
        for reservation in reservations
        if reservation.created_at.astimezone(LOCAL_TIMEZONE) >= last_30_days_start
    ]
    upcoming_7_days = [
        reservation
        for reservation in active_reservations
        if now
        <= reservation.start_datetime.astimezone(LOCAL_TIMEZONE)
        < next_7_days_end
    ]

    room_reservation_counts: Counter[int] = Counter()
    room_hours_counts: Counter[int] = Counter()
    for reservation in active_reservations:
        starts_in_period = (
            reservation.start_datetime.astimezone(LOCAL_TIMEZONE) >= last_30_days_start
        )
        if not starts_in_period:
            continue

        duration = reservation.end_datetime - reservation.start_datetime
        room_reservation_counts[reservation.room_id] += 1
        room_hours_counts[reservation.room_id] += duration.total_seconds() / 3600

    rooms_by_id = {room.room_id: room for room in rooms}
    top_rooms = [
        RoomUsage(
            room_id=room_id,
            room_name=rooms_by_id[room_id].name,
            reservations_count=count,
            hours_count=room_hours_counts[room_id],
        )
        for room_id, count in room_reservation_counts.most_common(5)
        if room_id in rooms_by_id
    ]

    return AdminAnalytics(
        users_count=len(users),
        admins_count=sum(1 for user in users if user.is_admin),
        rooms_count=len(rooms),
        active_rooms_count=sum(1 for room in rooms if room.is_active),
        reservations_count=len(reservations),
        active_reservations_count=len(active_reservations),
        canceled_reservations_count=len(canceled_reservations),
        created_last_30_days_count=len(created_last_30_days),
        upcoming_7_days_count=len(upcoming_7_days),
        top_rooms=top_rooms,
    )


def format_admin_analytics(analytics: AdminAnalytics) -> str:
    lines = [
        "Аналитика бронирований",
        "",
        f"Пользователи: {analytics.users_count}",
        f"Администраторы: {analytics.admins_count}",
        f"Комнаты: {analytics.active_rooms_count} активных из {analytics.rooms_count}",
        "",
        f"Всего бронирований: {analytics.reservations_count}",
        f"Активные бронирования: {analytics.active_reservations_count}",
        f"Отменённые бронирования: {analytics.canceled_reservations_count}",
        f"Создано за 30 дней: {analytics.created_last_30_days_count}",
        f"Предстоящие на 7 дней: {analytics.upcoming_7_days_count}",
        "",
        "Топ комнат за 30 дней:",
    ]

    if not analytics.top_rooms:
        lines.append("Пока нет активных бронирований за период.")
    else:
        for room in analytics.top_rooms:
            lines.append(
                f"#{room.room_id} {room.room_name}: "
                f"{room.reservations_count} брон., {room.hours_count:.1f} ч."
            )

    return "\n".join(lines)
