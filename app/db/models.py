from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    false,
    func,
    true,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    user_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    full_name: Mapped[str] = mapped_column(String(150), nullable=False)
    email: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, nullable=False, unique=True)
    is_admin: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=false(),
    )
    registered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    reservations: Mapped[list["Reservation"]] = relationship(
        back_populates="organizer",
        cascade="all, delete-orphan",
    )
    participations: Mapped[list["Participant"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )


class Room(Base):
    __tablename__ = "rooms"

    room_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    location: Mapped[str] = mapped_column(String(100), nullable=False)
    capacity: Mapped[int] = mapped_column(Integer, nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=true(),
    )

    reservations: Mapped[list["Reservation"]] = relationship(back_populates="room")
    equipment_items: Mapped[list["Equipment"]] = relationship(
        secondary="room_equipment",
        back_populates="rooms",
    )


class ReservationStatus(Base):
    __tablename__ = "reservation_statuses"

    status_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(30), nullable=False, unique=True)

    reservations: Mapped[list["Reservation"]] = relationship(back_populates="status")


class InvitationStatus(Base):
    __tablename__ = "invitation_statuses"

    invitation_status_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(30), nullable=False, unique=True)

    participants: Mapped[list["Participant"]] = relationship(
        back_populates="invitation_status"
    )


class EquipmentType(Base):
    __tablename__ = "equipment_types"

    type_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)

    equipment_items: Mapped[list["Equipment"]] = relationship(back_populates="type")


class Equipment(Base):
    __tablename__ = "equipment"

    equipment_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    part_number: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    type_id: Mapped[int] = mapped_column(
        ForeignKey("equipment_types.type_id"),
        nullable=False,
    )

    type: Mapped["EquipmentType"] = relationship(back_populates="equipment_items")
    rooms: Mapped[list["Room"]] = relationship(
        secondary="room_equipment",
        back_populates="equipment_items",
    )
    reservations: Mapped[list["Reservation"]] = relationship(
        secondary="reservation_equipment",
        back_populates="equipment_items",
    )


class RoomEquipment(Base):
    __tablename__ = "room_equipment"
    __table_args__ = (
        UniqueConstraint("room_id", "equipment_id", name="uq_room_equipment_pair"),
    )

    room_id: Mapped[int] = mapped_column(
        ForeignKey("rooms.room_id", ondelete="CASCADE"),
        primary_key=True,
    )
    equipment_id: Mapped[int] = mapped_column(
        ForeignKey("equipment.equipment_id", ondelete="CASCADE"),
        primary_key=True,
    )


class Reservation(Base):
    __tablename__ = "reservations"
    __table_args__ = (
        CheckConstraint(
            "end_datetime > start_datetime",
            name="ck_reservation_datetime_order",
        ),
        Index(
            "ix_reservations_room_time",
            "room_id",
            "start_datetime",
            "end_datetime",
        ),
    )

    reservation_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organizer_id: Mapped[int] = mapped_column(
        ForeignKey("users.user_id"),
        nullable=False,
    )
    room_id: Mapped[int] = mapped_column(
        ForeignKey("rooms.room_id"),
        nullable=False,
    )
    status_id: Mapped[int] = mapped_column(
        ForeignKey("reservation_statuses.status_id"),
        nullable=False,
    )
    start_datetime: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    end_datetime: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    purpose: Mapped[str] = mapped_column(String(200), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    organizer: Mapped["User"] = relationship(back_populates="reservations")
    room: Mapped["Room"] = relationship(back_populates="reservations")
    status: Mapped["ReservationStatus"] = relationship(back_populates="reservations")
    participants: Mapped[list["Participant"]] = relationship(
        back_populates="reservation",
        cascade="all, delete-orphan",
    )
    equipment_items: Mapped[list["Equipment"]] = relationship(
        secondary="reservation_equipment",
        back_populates="reservations",
    )


class Participant(Base):
    __tablename__ = "participants"
    __table_args__ = (
        UniqueConstraint("reservation_id", "user_id", name="uq_participant_user"),
    )

    participant_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    reservation_id: Mapped[int] = mapped_column(
        ForeignKey("reservations.reservation_id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
    )
    invitation_status_id: Mapped[int] = mapped_column(
        ForeignKey("invitation_statuses.invitation_status_id"),
        nullable=False,
    )

    reservation: Mapped["Reservation"] = relationship(back_populates="participants")
    user: Mapped["User"] = relationship(back_populates="participations")
    invitation_status: Mapped["InvitationStatus"] = relationship(
        back_populates="participants"
    )


class ReservationEquipment(Base):
    __tablename__ = "reservation_equipment"
    __table_args__ = (
        UniqueConstraint(
            "reservation_id",
            "equipment_id",
            name="uq_reservation_equipment_pair",
        ),
    )

    reservation_id: Mapped[int] = mapped_column(
        ForeignKey("reservations.reservation_id", ondelete="CASCADE"),
        primary_key=True,
    )
    equipment_id: Mapped[int] = mapped_column(
        ForeignKey("equipment.equipment_id", ondelete="CASCADE"),
        primary_key=True,
    )
