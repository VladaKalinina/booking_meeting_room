import os
import subprocess
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]

CHECKS = [
    [sys.executable, "-m", "compileall", "app", "scripts"],
    [sys.executable, "-c", "import main; print('MAIN_IMPORT_OK')"],
    [sys.executable, "scripts/check_db.py"],
    [sys.executable, "scripts/check_user_service.py"],
    [sys.executable, "scripts/check_registration.py"],
    [sys.executable, "scripts/check_rooms.py"],
    [sys.executable, "scripts/check_equipment.py"],
    [sys.executable, "scripts/check_schedule.py"],
    [sys.executable, "scripts/check_booking.py"],
    [sys.executable, "scripts/check_booking_edit.py"],
    [sys.executable, "scripts/check_my_reservations.py"],
    [sys.executable, "scripts/check_participants.py"],
    [sys.executable, "scripts/check_reminders.py"],
    [sys.executable, "scripts/check_admin_reservations.py"],
    [sys.executable, "scripts/check_user_management.py"],
    [sys.executable, "scripts/check_analytics.py"],
]


def format_command(command: list[str]) -> str:
    return " ".join(command)


def main() -> None:
    env = os.environ.copy()
    env.setdefault("PYTHONIOENCODING", "utf-8")

    for command in CHECKS:
        print(f"\n==> {format_command(command)}", flush=True)
        completed_process = subprocess.run(
            command,
            cwd=ROOT_DIR,
            env=env,
            check=False,
        )
        if completed_process.returncode != 0:
            raise SystemExit(completed_process.returncode)

    print("\nALL_CHECKS_OK")


if __name__ == "__main__":
    main()
