from datetime import UTC, datetime
from urllib.parse import urlencode
from uuid import uuid4

from app.db.models import Reservation
from app.services.schedule import LOCAL_TIMEZONE

LOCAL_TIMEZONE_ID = "Asia/Yekaterinburg"


def escape_ical_text(value: str) -> str:
    return (
        value.replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\r\n", "\\n")
        .replace("\n", "\\n")
    )


def format_ical_datetime(value: datetime) -> str:
    return value.astimezone(UTC).strftime("%Y%m%dT%H%M%SZ")


def format_local_ical_datetime(value: datetime) -> str:
    return value.astimezone(LOCAL_TIMEZONE).strftime("%Y%m%dT%H%M%S")


def fold_ical_line(line: str) -> list[str]:
    max_octets = 75
    encoded_line = line.encode("utf-8")
    if len(encoded_line) <= max_octets:
        return [line]

    folded_lines: list[str] = []
    current = ""
    current_octets = 0

    for char in line:
        char_octets = len(char.encode("utf-8"))
        if current and current_octets + char_octets > max_octets:
            folded_lines.append(current)
            current = " " + char
            current_octets = 1 + char_octets
        else:
            current += char
            current_octets += char_octets

    if current:
        folded_lines.append(current)

    return folded_lines


def build_ical_content(lines: list[str]) -> bytes:
    folded_lines = [
        folded_line
        for line in lines
        for folded_line in fold_ical_line(line)
    ]
    return ("\r\n".join(folded_lines) + "\r\n").encode("utf-8")


def build_reservation_ics(reservation: Reservation) -> bytes:
    room_name = reservation.room.name if reservation.room else f"Комната #{reservation.room_id}"
    created_at = reservation.created_at or datetime.now(LOCAL_TIMEZONE)
    uid = f"reservation-{reservation.reservation_id}-{uuid4()}@booking-meeting-room"
    summary = f"{reservation.purpose} — {room_name}"
    description = (
        f"Бронирование #{reservation.reservation_id}\n"
        f"Комната: {room_name}\n"
        f"Цель: {reservation.purpose}"
    )

    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Booking Meeting Room//Telegram Bot//RU",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "BEGIN:VTIMEZONE",
        f"TZID:{LOCAL_TIMEZONE_ID}",
        "BEGIN:STANDARD",
        "DTSTART:19700101T000000",
        "TZOFFSETFROM:+0500",
        "TZOFFSETTO:+0500",
        f"TZNAME:{LOCAL_TIMEZONE_ID}",
        "END:STANDARD",
        "END:VTIMEZONE",
        "BEGIN:VEVENT",
        f"UID:{uid}",
        f"DTSTAMP:{format_ical_datetime(created_at)}",
        f"DTSTART;TZID={LOCAL_TIMEZONE_ID}:{format_local_ical_datetime(reservation.start_datetime)}",
        f"DTEND;TZID={LOCAL_TIMEZONE_ID}:{format_local_ical_datetime(reservation.end_datetime)}",
        f"SUMMARY:{escape_ical_text(summary)}",
        f"LOCATION:{escape_ical_text(room_name)}",
        f"DESCRIPTION:{escape_ical_text(description)}",
        "STATUS:CONFIRMED",
        "TRANSP:OPAQUE",
        "END:VEVENT",
        "END:VCALENDAR",
    ]

    return build_ical_content(lines)


def reservation_ics_filename(reservation: Reservation) -> str:
    return f"reservation_{reservation.reservation_id}.ics"


def build_google_calendar_url(reservation: Reservation) -> str:
    room_name = reservation.room.name if reservation.room else f"Комната #{reservation.room_id}"
    params = {
        "action": "TEMPLATE",
        "text": f"{reservation.purpose} — {room_name}",
        "dates": (
            f"{format_ical_datetime(reservation.start_datetime)}/"
            f"{format_ical_datetime(reservation.end_datetime)}"
        ),
        "location": room_name,
        "details": (
            f"Бронирование #{reservation.reservation_id}\n"
            f"Комната: {room_name}\n"
            f"Цель: {reservation.purpose}"
        ),
    }
    return "https://calendar.google.com/calendar/render?" + urlencode(params)


def build_outlook_calendar_url(reservation: Reservation) -> str:
    room_name = reservation.room.name if reservation.room else f"Комната #{reservation.room_id}"
    params = {
        "path": "/calendar/action/compose",
        "rru": "addevent",
        "subject": f"{reservation.purpose} — {room_name}",
        "startdt": reservation.start_datetime.astimezone(UTC).isoformat(),
        "enddt": reservation.end_datetime.astimezone(UTC).isoformat(),
        "location": room_name,
        "body": (
            f"Бронирование #{reservation.reservation_id}\n"
            f"Комната: {room_name}\n"
            f"Цель: {reservation.purpose}"
        ),
    }
    return "https://outlook.live.com/calendar/0/deeplink/compose?" + urlencode(params)
