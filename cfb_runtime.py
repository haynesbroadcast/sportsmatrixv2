import json
import time
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from render.cfb_v2 import API, fetch, priority, render, OUTPUT

PT = ZoneInfo("America/Los_Angeles")

def event_time(event):
    return datetime.fromisoformat(
        event["date"].replace("Z", "+00:00")
    )

def relevant(events, now=None):
    now = now or datetime.now(timezone.utc)
    upcoming = []
    live = []
    finals = []

    for event in events:
        try:
            start = event_time(event)
            state = event["status"]["type"]["state"]
        except (KeyError, ValueError, TypeError):
            continue

        if state == "in":
            live.append(event)
        elif state == "pre" and now <= start <= now + timedelta(days=8):
            upcoming.append(event)
        elif state == "post" and now - timedelta(hours=4) <= start <= now:
            finals.append(event)

    live.sort(key=priority)
    upcoming.sort(key=priority)
    finals.sort(key=priority)

    # Keep the most relevant games, not stale results.
    return (live + upcoming + finals)[:10]

def fetch_events():
    now = datetime.now(PT)
    events_by_id = {}

    # ESPN's CFB endpoint accepts individual YYYYMMDD dates.
    # Check today and the next eight days.
    for offset in range(9):
        day = now + timedelta(days=offset)
        url = API + "&dates=" + day.strftime("%Y%m%d")

        try:
            data = json.loads(fetch(url))
        except Exception as exc:
            print("CFB schedule fetch failed:",
                  day.strftime("%Y-%m-%d"), exc)
            continue

        for event in data.get("events", []):
            if event.get("id"):
                events_by_id[str(event["id"])] = event

    return relevant(list(events_by_id.values()))

class CFBRotation:
    def __init__(self):
        self.events = []
        self.current_id = None
        self.last_schedule_fetch = 0
        self.last_live_fetch = 0
        self.last_rotate = time.monotonic()

    def tick(self):
        now = time.monotonic()

        # Full schedule refresh every five minutes.
        if not self.events or now - self.last_schedule_fetch >= 300:
            try:
                fresh = fetch_events()
                if fresh:
                    self.events = fresh
                self.last_schedule_fetch = now
            except Exception as exc:
                print("CFB schedule fetch failed:", exc)
                self.last_schedule_fetch = now

        # During live games, update today's scores every five seconds.
        live = any(
            e["status"]["type"]["state"] == "in"
            for e in self.events
        )

        if live and now - self.last_live_fetch >= 5:
            try:
                today = datetime.now(PT).strftime("%Y%m%d")
                data = json.loads(fetch(API + "&dates=" + today))
                updates = {
                    str(e["id"]): e
                    for e in data.get("events", [])
                }
                self.events = [
                    updates.get(str(e["id"]), e)
                    for e in self.events
                ]
                self.last_live_fetch = now
            except Exception as exc:
                print("CFB live fetch failed:", exc)
                self.last_live_fetch = now

        if not self.events:
            return None

        ids = [str(e["id"]) for e in self.events]

        if self.current_id not in ids:
            self.current_id = ids[0]
            self.last_rotate = now
        elif now - self.last_rotate >= 120:
            index = ids.index(self.current_id)
            self.current_id = ids[(index + 1) % len(ids)]
            self.last_rotate = now

        return next(
            e for e in self.events
            if str(e["id"]) == self.current_id
        )
