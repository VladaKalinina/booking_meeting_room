import asyncio
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.bot import create_bot
from app.config import load_config


async def main() -> None:
    config = load_config()
    bot = create_bot(config)

    try:
        me = await bot.get_me()
        print(f"BOT_OK username={me.username} id={me.id}")
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
