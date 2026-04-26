from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from app.config import Config
from app.handlers import router
from app.middlewares.db import DbSessionMiddleware


def create_bot(config: Config) -> Bot:
    session = AiohttpSession(proxy=config.telegram_proxy_url)

    return Bot(
        token=config.telegram_bot_token,
        session=session,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )


def create_dispatcher() -> Dispatcher:
    dispatcher = Dispatcher(storage=MemoryStorage())
    dispatcher.update.middleware(DbSessionMiddleware())
    dispatcher.include_router(router)
    return dispatcher
