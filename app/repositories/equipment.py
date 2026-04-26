from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import Equipment, EquipmentType, Room, RoomEquipment


async def list_equipment_types(session: AsyncSession) -> list[EquipmentType]:
    result = await session.execute(select(EquipmentType).order_by(EquipmentType.type_id))
    return list(result.scalars().all())


async def list_equipment(session: AsyncSession) -> list[Equipment]:
    result = await session.execute(
        select(Equipment)
        .options(selectinload(Equipment.type), selectinload(Equipment.rooms))
        .order_by(Equipment.equipment_id)
    )
    return list(result.scalars().all())


async def get_equipment_type_by_id(
    session: AsyncSession,
    type_id: int,
) -> EquipmentType | None:
    result = await session.execute(
        select(EquipmentType).where(EquipmentType.type_id == type_id)
    )
    return result.scalar_one_or_none()


async def get_equipment_type_by_name(
    session: AsyncSession,
    name: str,
) -> EquipmentType | None:
    result = await session.execute(select(EquipmentType).where(EquipmentType.name == name))
    return result.scalar_one_or_none()


async def get_equipment_by_id(
    session: AsyncSession,
    equipment_id: int,
) -> Equipment | None:
    result = await session.execute(
        select(Equipment)
        .options(selectinload(Equipment.type), selectinload(Equipment.rooms))
        .where(Equipment.equipment_id == equipment_id)
    )
    return result.scalar_one_or_none()


async def get_equipment_by_part_number(
    session: AsyncSession,
    part_number: str,
) -> Equipment | None:
    result = await session.execute(
        select(Equipment).where(Equipment.part_number == part_number)
    )
    return result.scalar_one_or_none()


async def get_room_equipment_link(
    session: AsyncSession,
    *,
    room_id: int,
    equipment_id: int,
) -> RoomEquipment | None:
    result = await session.execute(
        select(RoomEquipment).where(
            RoomEquipment.room_id == room_id,
            RoomEquipment.equipment_id == equipment_id,
        )
    )
    return result.scalar_one_or_none()


async def add_equipment_type(session: AsyncSession, *, name: str) -> EquipmentType:
    equipment_type = EquipmentType(name=name)
    session.add(equipment_type)
    await session.flush()
    return equipment_type


async def add_equipment(
    session: AsyncSession,
    *,
    part_number: str,
    type_id: int,
) -> Equipment:
    equipment = Equipment(part_number=part_number, type_id=type_id)
    session.add(equipment)
    await session.flush()
    return equipment


async def add_room_equipment_link(
    session: AsyncSession,
    *,
    room_id: int,
    equipment_id: int,
) -> RoomEquipment:
    link = RoomEquipment(room_id=room_id, equipment_id=equipment_id)
    session.add(link)
    await session.flush()
    return link
