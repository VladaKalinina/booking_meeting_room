from dataclasses import dataclass
from datetime import date, datetime, time

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Reservation, Room, User
from app.repositories.reservations import (
    ACTIVE_RESERVATION_STATUS_IDS,
    add_reservation,
    add_reservation_equipment_link,
    get_reservation_by_id,
    list_active_reservations_by_organizer,
    list_reservations_for_period,
)
from app.repositories.rooms import get_room_by_id, list_rooms
from app.services.rooms import validate_capacity
from app.services.schedule import LOCAL_TIMEZONE

CONFIRMED_STATUS_ID = 1
CANCELED_STATUS_ID = 3


@dataclass(frozen=True)
class BookingDraft:
    start_at: datetime
    end_at: datetime
    purpose: str
    capacity: int
    equipment_type_ids: list[int]


def parse_time(value: str) -> time:
    normalized_value = value.strip()
    for time_format in ("%H:%M", "%H.%M"):
        try:
            return datetime.strptime(normalized_value, time_format).time()
        except ValueError:
            continue

    raise ValueError("Введите время в формате ЧЧ:ММ, например 09:30.")


def combine_date_time(value_date: date, value_time: time) -> datetime:
    return datetime.combine(value_date, value_time, tzinfo=LOCAL_TIMEZONE)


def parse_equipment_type_ids(value: str) -> list[int]:
    normalized_value = value.strip().lower()
    if normalized_value in {"", "нет", "не нужно", "none", "-"}:
        return []

    parts = [part.strip() for part in normalized_value.replace(";", ",").split(",")]
    type_ids: list[int] = []
    for part in parts:
        if not part:
            continue
        if not part.isdigit():
            raise ValueError("Введите ID типов оборудования через запятую или слово 'нет'.")
        type_ids.append(int(part))

    return sorted(set(type_ids))


def validate_booking_time(start_at: datetime, end_at: datetime) -> None:
    now = datetime.now(LOCAL_TIMEZONE)
    if start_at < now:
        raise ValueError("Нельзя создать бронирование в прошлом.")
    if end_at <= start_at:
        raise ValueError("Время окончания должно быть позже времени начала.")


def room_has_required_equipment(room: Room, equipment_type_ids: list[int]) -> bool:
    room_equipment_type_ids = {item.type_id for item in room.equipment_items}
    return set(equipment_type_ids).issubset(room_equipment_type_ids)


def reservation_overlaps(
    *,
    reservation_start: datetime,
    reservation_end: datetime,
    start_at: datetime,
    end_at: datetime,
) -> bool:
    return reservation_start < end_at and reservation_end > start_at


async def get_available_rooms(
    session: AsyncSession,
    *,
    start_at: datetime,
    end_at: datetime,
    capacity: int,
    equipment_type_ids: list[int],
) -> list[Room]:
    validate_booking_time(start_at, end_at)
    validate_capacity(capacity)

    rooms = [
        room
        for room in await list_rooms(session)
        if room.is_active
        and room.capacity >= capacity
        and room_has_required_equipment(room, equipment_type_ids)
    ]

    reservations = await list_reservations_for_period(
        session,
        start_at=start_at,
        end_at=end_at,
    )
    busy_room_ids = {
        reservation.room_id
        for reservation in reservations
        if reservation.status_id in ACTIVE_RESERVATION_STATUS_IDS
        and reservation_overlaps(
            reservation_start=reservation.start_datetime,
            reservation_end=reservation.end_datetime,
            start_at=start_at,
            end_at=end_at,
        )
    }

    return [room for room in rooms if room.room_id not in busy_room_ids]


def choose_room_equipment_ids(room: Room, equipment_type_ids: list[int]) -> list[int]:
    selected_equipment_ids: list[int] = []
    for type_id in equipment_type_ids:
        equipment = next(
            item for item in room.equipment_items if item.type_id == type_id
        )
        selected_equipment_ids.append(equipment.equipment_id)
    return selected_equipment_ids


async def create_booking(
    session: AsyncSession,
    *,
    organizer: User,
    room_id: int,
    draft: BookingDraft,
) -> Reservation:
    available_rooms = await get_available_rooms(
        session,
        start_at=draft.start_at,
        end_at=draft.end_at,
        capacity=draft.capacity,
        equipment_type_ids=draft.equipment_type_ids,
    )
    available_room_ids = {room.room_id for room in available_rooms}
    if room_id not in available_room_ids:
        raise ValueError("Выбранная комната уже недоступна для этого интервала.")

    room = await get_room_by_id(session, room_id)
    if not room:
        raise ValueError("Комната не найдена.")

    reservation = await add_reservation(
        session,
        organizer_id=organizer.user_id,
        room_id=room_id,
        status_id=CONFIRMED_STATUS_ID,
        start_datetime=draft.start_at,
        end_datetime=draft.end_at,
        purpose=draft.purpose,
    )

    for equipment_id in choose_room_equipment_ids(room, draft.equipment_type_ids):
        await add_reservation_equipment_link(
            session,
            reservation_id=reservation.reservation_id,
            equipment_id=equipment_id,
        )

    return reservation


async def get_my_active_reservations(
    session: AsyncSession,
    *,
    organizer: User,
) -> list[Reservation]:
    return await list_active_reservations_by_organizer(session, organizer.user_id)


async def cancel_own_reservation(
    session: AsyncSession,
    *,
    organizer: User,
    reservation_id: int,
) -> Reservation:
    reservation = await get_reservation_by_id(session, reservation_id)
    if not reservation:
        raise ValueError("Бронирование не найдено.")
    if reservation.organizer_id != organizer.user_id:
        raise ValueError("Можно отменить только своё бронирование.")
    if reservation.status_id not in ACTIVE_RESERVATION_STATUS_IDS:
        raise ValueError("Это бронирование уже не активно.")

    reservation.status_id = CANCELED_STATUS_ID
    await session.flush()
    return reservation
