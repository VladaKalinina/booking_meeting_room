import asyncio
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.db.session import async_session_factory, engine
from app.services.rooms import create_room, deactivate_room, get_rooms


async def main() -> None:
    async with async_session_factory() as session:
        async with session.begin():
            room = await create_room(
                session,
                name="Большая переговорная",
                location="3 этаж, офис 305",
                capacity=12,
            )
            assert room.room_id is not None
            assert room.is_active is True

            rooms = await get_rooms(session)
            assert any(item.room_id == room.room_id for item in rooms)

            deactivated_room = await deactivate_room(session, room.room_id)
            assert deactivated_room.is_active is False

            await session.rollback()

    await engine.dispose()
    print("ROOMS_OK")


if __name__ == "__main__":
    asyncio.run(main())
