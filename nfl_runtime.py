
import json
import time
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from render.nfl_v2 import API, fetch, priority

PT = ZoneInfo("America/Los_Angeles")


def event_time(event):
    return datetime.fromisoformat(
        event["date"].replace("Z", "+00:00")
    )


def relevant(events):
    now = datetime.now(timezone.utc)
    result = []

    for event in events:
        try:
            start = event_time(event)
            state = event["status"]["type"]["state"]
        except (KeyError, ValueError, TypeError):
            continue

        if state == "in":
            result.append(event)
        elif state == "pre" and now <= start <= now + timedelta(days=8):
            result.append(event)
        elif state == "post" and now - timedelta(days=7) <= start <= now:
            result.append(event)

    return sorted(result, key=priority)


def fetch_events():
    now = datetime.now(PT)
    events = {}

    # Fetch the previous two days and the next eight.
    # NFL schedules can span multiple calendar dates.
    for offset in range(-2, 9):
        day = now + timedelta(days=offset)
        url = API + "&dates=" + day.strftime("%Y%m%d")

        try:
            data = json.loads(fetch(url))
        except Exception as exc:
            print("NFL fetch failed:", day.date(), exc)
            continue

        for event in data.get("events", []):
            if event.get("id"):
                events[str(event["id"])] = event

    return relevant(list(events.values()))


class NFLRotation:
    def __init__(self):
        self.events = []
        self.current_id = None
        self.last_schedule_fetch = 0
        self.last_live_fetch = 0
        self.last_rotate = time.monotonic()

    def tick(self):
        now = time.monotonic()

        if not self.events or now - self.last_schedule_fetch >= 300:
            try:
                fresh = fetch_events()
                if fresh:
                    self.events = fresh
                self.last_schedule_fetch = now
            except Exception as exc:
                print("NFL schedule error:", exc)
                self.last_schedule_fetch = now

        live = [
            e for e in self.events
            if e.get("status", {}).get("type", {}).get("state") == "in"
        ]

        if live and now - self.last_live_fetch >= 5:
            try:
                dates = {
                    event_time(e).astimezone(PT).strftime("%Y%m%d")
                    for e in live
                }
                updates = {}

                for day in dates:
                    data = json.loads(fetch(API + "&dates=" + day))
                    for e in data.get("events", []):
                        updates[str(e["id"])] = e

                self.events = [
                    updates.get(str(e["id"]), e)
                    for e in self.events
                ]
            except Exception as exc:
                print("NFL live update error:", exc)
            finally:
                self.last_live_fetch = now

        if not self.events:
            return None

        # Reorder after score/status changes.
        self.events = sorted(self.events, key=priority)
        ids = [str(e["id"]) for e in self.events]

        if self.current_id not in ids:
            self.current_id = ids[0]
            self.last_rotate = now
        elif now - self.last_rotate >= 30:
            index = ids.index(self.current_id)
            self.current_id = ids[(index + 1) % len(ids)]
            self.last_rotate = now

        return next(
            e for e in self.events
            if str(e["id"]) == self.current_id
        )
