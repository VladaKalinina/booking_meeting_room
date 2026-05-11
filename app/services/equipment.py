from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Equipment, EquipmentType, RoomEquipment
from app.repositories.equipment import (
    add_equipment,
    add_equipment_type,
    add_room_equipment_link,
    delete_equipment,
    delete_room_equipment_link,
    get_equipment_by_id,
    get_equipment_by_part_number,
    get_equipment_type_by_id,
    get_equipment_type_by_name,
    get_room_equipment_link,
    list_equipment,
    list_equipment_types,
)
from app.repositories.rooms import get_room_by_id


def normalize_text(value: str) -> str:
    return " ".join(value.split())


async def get_equipment_types(session: AsyncSession) -> list[EquipmentType]:
    return await list_equipment_types(session)


async def get_equipment_items(session: AsyncSession) -> list[Equipment]:
    return await list_equipment(session)


async def create_equipment_type(session: AsyncSession, *, name: str) -> EquipmentType:
    normalized_name = normalize_text(name)
    if not normalized_name:
        raise ValueError("Название типа оборудования не может быть пустым.")
    if len(normalized_name) > 50:
        raise ValueError("Название типа оборудования должно быть не длиннее 50 символов.")

    existing_type = await get_equipment_type_by_name(session, normalized_name)
    if existing_type:
        raise ValueError("Такой тип оборудования уже существует.")

    return await add_equipment_type(session, name=normalized_name)


async def create_equipment(
    session: AsyncSession,
    *,
    part_number: str,
    type_id: int,
) -> Equipment:
    normalized_part_number = normalize_text(part_number)
    if not normalized_part_number:
        raise ValueError("Инвентарный номер не может быть пустым.")
    if len(normalized_part_number) > 50:
        raise ValueError("Инвентарный номер должен быть не длиннее 50 символов.")

    equipment_type = await get_equipment_type_by_id(session, type_id)
    if not equipment_type:
        raise ValueError("Тип оборудования не найден.")

    existing_equipment = await get_equipment_by_part_number(
        session,
        normalized_part_number,
    )
    if existing_equipment:
        raise ValueError("Оборудование с таким инвентарным номером уже существует.")

    return await add_equipment(
        session,
        part_number=normalized_part_number,
        type_id=type_id,
    )


async def attach_equipment_to_room(
    session: AsyncSession,
    *,
    room_id: int,
    equipment_id: int,
) -> RoomEquipment:
    room = await get_room_by_id(session, room_id)
    if not room:
        raise ValueError("Комната не найдена.")

    equipment = await get_equipment_by_id(session, equipment_id)
    if not equipment:
        raise ValueError("Оборудование не найдено.")

    existing_link = await get_room_equipment_link(
        session,
        room_id=room_id,
        equipment_id=equipment_id,
    )
    if existing_link:
        raise ValueError("Это оборудование уже привязано к выбранной комнате.")

    return await add_room_equipment_link(
        session,
        room_id=room_id,
        equipment_id=equipment_id,
    )


async def detach_equipment_from_room(
    session: AsyncSession,
    *,
    room_id: int,
    equipment_id: int,
) -> None:
    room = await get_room_by_id(session, room_id)
    if not room:
        raise ValueError("Комната не найдена.")

    equipment = await get_equipment_by_id(session, equipment_id)
    if not equipment:
        raise ValueError("Оборудование не найдено.")

    existing_link = await get_room_equipment_link(
        session,
        room_id=room_id,
        equipment_id=equipment_id,
    )
    if not existing_link:
        raise ValueError("Это оборудование не привязано к выбранной комнате.")

    await delete_room_equipment_link(session, existing_link)


async def remove_equipment(session: AsyncSession, *, equipment_id: int) -> Equipment:
    equipment = await get_equipment_by_id(session, equipment_id)
    if not equipment:
        raise ValueError("Оборудование не найдено.")

    await delete_equipment(session, equipment)
    return equipment
