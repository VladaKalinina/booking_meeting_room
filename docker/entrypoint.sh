#!/bin/sh
set -e

python - <<'PY'
import asyncio
import os

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine


async def main() -> None:
    database_url = os.environ["DATABASE_URL"]

    for attempt in range(1, 61):
        engine = create_async_engine(database_url)
        try:
            async with engine.connect() as connection:
                await connection.execute(text("select 1"))
            print("Database is ready", flush=True)
            return
        except Exception as error:
            print(f"Waiting for database ({attempt}/60): {error}", flush=True)
            await asyncio.sleep(2)
        finally:
            await engine.dispose()

    raise SystemExit("Database is not ready")


asyncio.run(main())
PY

python -m alembic upgrade head
python main.py
