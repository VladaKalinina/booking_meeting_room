from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import load_config

config = load_config()

if not config.database_url:
    raise RuntimeError("DATABASE_URL is not set. Add it to .env before using the database.")

engine = create_async_engine(config.database_url, echo=False)
async_session_factory = async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    async with async_session_factory() as session:
        yield session
