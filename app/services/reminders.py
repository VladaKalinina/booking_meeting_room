import asyncio
import contextlib
import logging
from datetime import datetime, timedelta

from aiogram import Bot

from app.db.session import async_session_factory
from app.repositories.reservations import ACTIVE_RESERVATION_STATUS_IDS
from app.services.bookings import get_all_reservations
from app.services.participants import ACCEPTED_INVITATION_STATUS_ID
from app.services.schedule import LOCAL_TIMEZONE

REMINDER_BEFORE_START = timedelta(minutes=15)
REMINDER_LOOKAHEAD = timedelta(minutes=1)
REMINDER_CHECK_INTERVAL_SECONDS = 60


def format_reservation_reminder(reservation) -> str:
    start_at = reservation.start_datetime.astimezone(LOCAL_TIMEZONE).strftime("%H:%M")
    return (
        "Напоминание о встрече.\n"
        f"Начало через 15 минут: {start_at}\n"
        f"Комната: {reservation.room.name}\n"
        f"Цель: {reservation.purpose}"
    )


def reservation_should_be_reminded(reservation, now: datetime) -> bool:
    reminder_at = reservation.start_datetime.astimezone(LOCAL_TIMEZONE) - REMINDER_BEFORE_START
    return now <= reminder_at < now + REMINDER_LOOKAHEAD


async def send_reservation_reminder(bot: Bot, reservation) -> None:
    text = format_reservation_reminder(reservation)
    await bot.send_message(reservation.organizer.telegram_id, text)

    for participant in reservation.participants:
        if participant.invitation_status_id == ACCEPTED_INVITATION_STATUS_ID:
            await bot.send_message(participant.user.telegram_id, text)


async def run_reminder_loop(bot: Bot) -> None:
    sent_reservation_ids: set[int] = set()

    while True:
        try:
            now = datetime.now(LOCAL_TIMEZONE)
            async with async_session_factory() as session:
                reservations = await get_all_reservations(session)

            for reservation in reservations:
                if reservation.reservation_id in sent_reservation_ids:
                    continue
                if reservation.status_id not in ACTIVE_RESERVATION_STATUS_IDS:
                    continue
                if not reservation_should_be_reminded(reservation, now):
                    continue

                await send_reservation_reminder(bot, reservation)
                sent_reservation_ids.add(reservation.reservation_id)
        except asyncio.CancelledError:
            raise
        except Exception:
            logging.exception("Failed to send reservation reminders")

        await asyncio.sleep(REMINDER_CHECK_INTERVAL_SECONDS)


async def stop_reminder_loop(task: asyncio.Task | None) -> None:
    if not task:
        return

    task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await task
