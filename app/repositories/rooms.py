from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import Room


async def list_rooms(session: AsyncSession) -> list[Room]:
    result = await session.execute(
        select(Room)
        .options(selectinload(Room.equipment_items))
        .order_by(Room.room_id)
        .execution_options(populate_existing=True)
    )
    return list(result.scalars().all())


async def get_room_by_id(session: AsyncSession, room_id: int) -> Room | None:
    result = await session.execute(
        select(Room)
        .options(selectinload(Room.equipment_items))
        .where(Room.room_id == room_id)
        .execution_options(populate_existing=True)
    )
    return result.scalar_one_or_none()


async def add_room(
    session: AsyncSession,
    *,
    name: str,
    location: str,
    capacity: int,
) -> Room:
    room = Room(name=name, location=location, capacity=capacity)
    session.add(room)
    await session.flush()
    return room
