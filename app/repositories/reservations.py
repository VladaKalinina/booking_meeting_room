from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import Reservation, ReservationEquipment

ACTIVE_RESERVATION_STATUS_IDS = (1, 2)


async def list_reservations_for_period(
    session: AsyncSession,
    *,
    start_at: datetime,
    end_at: datetime,
) -> list[Reservation]:
    result = await session.execute(
        select(Reservation)
        .options(
            selectinload(Reservation.room),
            selectinload(Reservation.status),
            selectinload(Reservation.organizer),
        )
        .where(
            Reservation.status_id.in_(ACTIVE_RESERVATION_STATUS_IDS),
            Reservation.start_datetime < end_at,
            Reservation.end_datetime > start_at,
        )
        .order_by(Reservation.start_datetime, Reservation.room_id)
    )
    return list(result.scalars().all())


async def list_active_reservations_by_organizer(
    session: AsyncSession,
    organizer_id: int,
) -> list[Reservation]:
    result = await session.execute(
        select(Reservation)
        .options(
            selectinload(Reservation.room),
            selectinload(Reservation.status),
            selectinload(Reservation.equipment_items),
        )
        .where(
            Reservation.organizer_id == organizer_id,
            Reservation.status_id.in_(ACTIVE_RESERVATION_STATUS_IDS),
        )
        .order_by(Reservation.start_datetime, Reservation.reservation_id)
    )
    return list(result.scalars().all())


async def get_reservation_by_id(
    session: AsyncSession,
    reservation_id: int,
) -> Reservation | None:
    result = await session.execute(
        select(Reservation)
        .options(
            selectinload(Reservation.room),
            selectinload(Reservation.status),
            selectinload(Reservation.organizer),
        )
        .where(Reservation.reservation_id == reservation_id)
    )
    return result.scalar_one_or_none()


async def add_reservation(
    session: AsyncSession,
    *,
    organizer_id: int,
    room_id: int,
    status_id: int,
    start_datetime: datetime,
    end_datetime: datetime,
    purpose: str,
) -> Reservation:
    reservation = Reservation(
        organizer_id=organizer_id,
        room_id=room_id,
        status_id=status_id,
        start_datetime=start_datetime,
        end_datetime=end_datetime,
        purpose=purpose,
    )
    session.add(reservation)
    await session.flush()
    return reservation


async def add_reservation_equipment_link(
    session: AsyncSession,
    *,
    reservation_id: int,
    equipment_id: int,
) -> ReservationEquipment:
    link = ReservationEquipment(
        reservation_id=reservation_id,
        equipment_id=equipment_id,
    )
    session.add(link)
    await session.flush()
    return link
