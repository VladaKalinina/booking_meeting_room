from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import Participant, Reservation, User
from app.repositories.reservations import ACTIVE_RESERVATION_STATUS_IDS, get_reservation_by_id
from app.repositories.users import get_user_by_email

PENDING_INVITATION_STATUS_ID = 1
ACCEPTED_INVITATION_STATUS_ID = 2
DECLINED_INVITATION_STATUS_ID = 3


@dataclass(frozen=True)
class ParticipantAddResult:
    added: list[Participant]
    already_invited: list[User]
    not_found_emails: list[str]


def parse_participant_emails(value: str) -> list[str]:
    emails = [
        item.strip().lower()
        for item in value.replace(";", ",").split(",")
        if item.strip()
    ]
    return sorted(set(emails))


async def list_reservation_participants(
    session: AsyncSession,
    *,
    reservation_id: int,
) -> list[Participant]:
    result = await session.execute(
        select(Participant)
        .options(
            selectinload(Participant.user),
            selectinload(Participant.invitation_status),
        )
        .where(Participant.reservation_id == reservation_id)
        .order_by(Participant.participant_id)
    )
    return list(result.scalars().all())


async def add_participants_by_email(
    session: AsyncSession,
    *,
    organizer: User,
    reservation_id: int,
    emails: list[str],
) -> ParticipantAddResult:
    reservation = await get_reservation_by_id(session, reservation_id)
    if not reservation:
        raise ValueError("Бронирование не найдено.")
    if reservation.organizer_id != organizer.user_id:
        raise ValueError("Можно добавлять участников только в своё бронирование.")
    if reservation.status_id not in ACTIVE_RESERVATION_STATUS_IDS:
        raise ValueError("Нельзя добавлять участников в неактивное бронирование.")

    existing_participants = await list_reservation_participants(
        session,
        reservation_id=reservation_id,
    )
    existing_user_ids = {participant.user_id for participant in existing_participants}

    added: list[Participant] = []
    already_invited: list[User] = []
    not_found_emails: list[str] = []

    for email in emails:
        user = await get_user_by_email(session, email)
        if not user:
            not_found_emails.append(email)
            continue
        if user.user_id == organizer.user_id or user.user_id in existing_user_ids:
            already_invited.append(user)
            continue

        participant = Participant(
            reservation_id=reservation_id,
            user_id=user.user_id,
            invitation_status_id=PENDING_INVITATION_STATUS_ID,
        )
        session.add(participant)
        await session.flush()
        added.append(participant)
        existing_user_ids.add(user.user_id)

    for participant in added:
        await session.refresh(participant, attribute_names=["user", "invitation_status"])

    return ParticipantAddResult(
        added=added,
        already_invited=already_invited,
        not_found_emails=not_found_emails,
    )


async def get_participant_by_id(
    session: AsyncSession,
    participant_id: int,
) -> Participant | None:
    result = await session.execute(
        select(Participant)
        .options(
            selectinload(Participant.user),
            selectinload(Participant.reservation).selectinload(Reservation.organizer),
            selectinload(Participant.reservation).selectinload(Reservation.room),
            selectinload(Participant.invitation_status),
        )
        .where(Participant.participant_id == participant_id)
    )
    return result.scalar_one_or_none()


async def set_invitation_status(
    session: AsyncSession,
    *,
    participant_id: int,
    telegram_id: int,
    status_id: int,
) -> Participant:
    participant = await get_participant_by_id(session, participant_id)
    if not participant:
        raise ValueError("Приглашение не найдено.")
    if participant.user.telegram_id != telegram_id:
        raise ValueError("Это приглашение адресовано другому пользователю.")
    if status_id not in {ACCEPTED_INVITATION_STATUS_ID, DECLINED_INVITATION_STATUS_ID}:
        raise ValueError("Некорректный статус приглашения.")

    participant.invitation_status_id = status_id
    await session.flush()
    await session.refresh(participant, attribute_names=["invitation_status"])
    return participant


def format_participants(participants: list[Participant]) -> str:
    if not participants:
        return "У бронирования пока нет участников."

    lines = ["Участники бронирования:"]
    for participant in participants:
        lines.append(
            f"#{participant.participant_id}: {participant.user.full_name} "
            f"({participant.user.email}) — {participant.invitation_status.name}"
        )
    return "\n".join(lines)
