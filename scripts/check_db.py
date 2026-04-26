import asyncio
import sys
from pathlib import Path

from sqlalchemy import text

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.db.session import engine


async def main() -> None:
    async with engine.connect() as connection:
        tables = await connection.execute(
            text(
                """
                select table_name
                from information_schema.tables
                where table_schema = 'public'
                order by table_name
                """
            )
        )
        reservation_statuses = await connection.execute(
            text("select status_id, name from reservation_statuses order by status_id")
        )
        invitation_statuses = await connection.execute(
            text(
                "select invitation_status_id, name from invitation_statuses "
                "order by invitation_status_id"
            )
        )

        print("TABLES=" + ", ".join(row.table_name for row in tables))
        print(
            "RESERVATION_STATUSES="
            + ", ".join(f"{row.status_id}:{row.name}" for row in reservation_statuses)
        )
        print(
            "INVITATION_STATUSES="
            + ", ".join(
                f"{row.invitation_status_id}:{row.name}" for row in invitation_statuses
            )
        )

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
