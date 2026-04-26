from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Room
from app.repositories.rooms import add_room, get_room_by_id, list_rooms


def normalize_room_text(value: str) -> str:
    return " ".join(value.split())


def validate_capacity(capacity: int) -> None:
    if capacity <= 0:
        raise ValueError("Вместимость должна быть положительным числом.")
    if capacity > 500:
        raise ValueError("Вместимость выглядит слишком большой. Укажите значение до 500.")


async def get_rooms(session: AsyncSession) -> list[Room]:
    return await list_rooms(session)


async def create_room(
    session: AsyncSession,
    *,
    name: str,
    location: str,
    capacity: int,
) -> Room:
    normalized_name = normalize_room_text(name)
    normalized_location = normalize_room_text(location)

    if not normalized_name:
        raise ValueError("Название комнаты не может быть пустым.")
    if len(normalized_name) > 100:
        raise ValueError("Название комнаты должно быть не длиннее 100 символов.")
    if not normalized_location:
        raise ValueError("Локация комнаты не может быть пустой.")
    if len(normalized_location) > 100:
        raise ValueError("Локация комнаты должна быть не длиннее 100 символов.")

    validate_capacity(capacity)

    return await add_room(
        session,
        name=normalized_name,
        location=normalized_location,
        capacity=capacity,
    )


async def deactivate_room(session: AsyncSession, room_id: int) -> Room:
    room = await get_room_by_id(session, room_id)
    if not room:
        raise ValueError("Комната не найдена.")

    room.is_active = False
    await session.flush()
    return room
