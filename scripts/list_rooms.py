import asyncio
import sys
from pathlib import Path

from sqlalchemy import text

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.db.session import async_session_factory, engine


async def main() -> None:
    async with async_session_factory() as session:
        rooms = await session.execute(
            text("select room_id, name, location, capacity, is_active from rooms order by room_id")
        )
        reservations = await session.execute(
            text(
                """
                select reservation_id, room_id, purpose, status_id
                from reservations
                order by reservation_id
                """
            )
        )

        print("ROOMS")
        for row in rooms:
            print(
                f"{row.room_id}: {row.name!r}, {row.location!r}, "
                f"capacity={row.capacity}, is_active={row.is_active}"
            )

        print("RESERVATIONS")
        for row in reservations:
            print(
                f"{row.reservation_id}: room_id={row.room_id}, "
                f"purpose={row.purpose!r}, status_id={row.status_id}"
            )

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
