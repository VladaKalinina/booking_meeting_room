import asyncio
import contextlib
import logging
import socket
import sys

from app.bot import create_bot, create_dispatcher
from app.config import load_config

SINGLE_INSTANCE_HOST = "127.0.0.1"
SINGLE_INSTANCE_PORT = 8765


@contextlib.contextmanager
def single_instance_lock():
    lock_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        lock_socket.bind((SINGLE_INSTANCE_HOST, SINGLE_INSTANCE_PORT))
        lock_socket.listen(1)
        yield
    except OSError as error:
        raise RuntimeError(
            "Bot is already running. Stop the existing main.py process before starting another one."
        ) from error
    finally:
        lock_socket.close()


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
    try:
        with single_instance_lock():
            asyncio.run(main())
    except RuntimeError as error:
        print(error, file=sys.stderr)
        raise SystemExit(1)
