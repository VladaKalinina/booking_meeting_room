import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass(frozen=True)
class Config:
    telegram_bot_token: str
    telegram_proxy_url: str | None = None
    database_url: str | None = None


def load_config() -> Config:
    load_dotenv()

    telegram_bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not telegram_bot_token:
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN is not set. Create .env from .env.example and add your bot token."
        )

    telegram_proxy_url = os.getenv("TELEGRAM_PROXY_URL") or None
    database_url = os.getenv("DATABASE_URL") or None

    return Config(
        telegram_bot_token=telegram_bot_token,
        telegram_proxy_url=telegram_proxy_url,
        database_url=database_url,
    )
