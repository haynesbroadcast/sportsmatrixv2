import json
import subprocess
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

BASE = Path("/home/scoreboard/sports/sportsmatrix_mvp")
SETTINGS = BASE / "config/settings.json"

SERVICES = [
    "sportsmatrix",
    "mlb-scoreboard",
    "nfl-scoreboard",
]


def load_settings():
    return json.loads(SETTINGS.read_text())


def service_active(name):
    result = subprocess.run(
        ["systemctl", "is-active", "--quiet", name]
    )
    return result.returncode == 0


def any_display_running():
    return any(service_active(s) for s in SERVICES)


def stop_display():
    for service in SERVICES:
        subprocess.run(["systemctl", "stop", service])


def start_selected(league):
    subprocess.run([
        str(BASE / ".venv/bin/python"),
        str(BASE / "switch_sport.py"),
        league,
    ])


def in_display_window(now, on_time, off_time):
    on_minutes = int(on_time[:2]) * 60 + int(on_time[3:])
    off_minutes = int(off_time[:2]) * 60 + int(off_time[3:])
    now_minutes = now.hour * 60 + now.minute

    if on_minutes < off_minutes:
        return on_minutes <= now_minutes < off_minutes

    # Supports schedules crossing midnight.
    return now_minutes >= on_minutes or now_minutes < off_minutes


def enforce():
    settings = load_settings()
    schedule = settings.get("display_schedule", {})

    override = schedule.get("override", "auto")

    if override == "off":
        if any_display_running():
            stop_display()
        return

    if override == "on":
        if not any_display_running():
            start_selected(settings.get("league", "worldcup"))
        return

    if not schedule.get("enabled", False):
        return

    tz = ZoneInfo(settings.get("timezone", "America/Los_Angeles"))
    now = datetime.now(tz)

    should_run = in_display_window(
        now,
        schedule.get("on_time", "07:00"),
        schedule.get("off_time", "23:00"),
    )

    running = any_display_running()

    if should_run and not running:
        league = settings.get("league", "worldcup")
        print(f"{now}: display hours active — starting {league}", flush=True)
        start_selected(league)

    elif not should_run and running:
        print(f"{now}: outside display hours — stopping display", flush=True)
        stop_display()


def main():
    print("SportsMatrix display schedule started", flush=True)

    while True:
        try:
            enforce()
        except Exception as e:
            print(f"Schedule error: {e}", flush=True)

        time.sleep(30)


if __name__ == "__main__":
    main()
