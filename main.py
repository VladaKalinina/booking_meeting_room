import asyncio
import logging

from app.bot import create_bot, create_dispatcher
from app.config import load_config


async def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    config = load_config()
    bot = create_bot(config)
    dispatcher = create_dispatcher()

    logging.info("Booking meeting room bot is starting")
    await dispatcher.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
