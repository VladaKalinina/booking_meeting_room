import asyncio
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.db.session import async_session_factory, engine
from app.services.equipment import (
    attach_equipment_to_room,
    create_equipment,
    create_equipment_type,
    get_equipment_items,
    get_equipment_types,
)
from app.services.rooms import create_room


async def main() -> None:
    async with async_session_factory() as session:
        async with session.begin():
            room = await create_room(
                session,
                name="Тестовая переговорная",
                location="2 этаж",
                capacity=8,
            )
            equipment_type = await create_equipment_type(session, name="Проектор")
            equipment = await create_equipment(
                session,
                type_id=equipment_type.type_id,
                part_number="PRJ-TEST-001",
            )
            link = await attach_equipment_to_room(
                session,
                room_id=room.room_id,
                equipment_id=equipment.equipment_id,
            )

            assert link.room_id == room.room_id
            assert link.equipment_id == equipment.equipment_id
            assert any(item.type_id == equipment_type.type_id for item in await get_equipment_types(session))
            assert any(item.equipment_id == equipment.equipment_id for item in await get_equipment_items(session))

            await session.rollback()

    await engine.dispose()
    print("EQUIPMENT_OK")


if __name__ == "__main__":
    asyncio.run(main())
