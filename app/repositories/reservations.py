from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import Reservation

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
