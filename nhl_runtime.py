
import json
import time
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from pathlib import Path
from render.nhl_v2 import API, fetch, priority

PT = ZoneInfo("America/Los_Angeles")
SETTINGS = Path(__file__).resolve().parent / "config/settings.json"

def preferences():
    try:
        data = json.loads(SETTINGS.read_text())
        return data.get("sport_preferences", {}).get("nhl", {})
    except (OSError, ValueError):
        return {}

def event_time(event):
    return datetime.fromisoformat(event["date"].replace("Z", "+00:00"))

def has_team(event, abbreviation):
    aliases = {"SJ": {"SJ", "SJS"}, "SJS": {"SJ", "SJS"}}
    wanted = aliases.get(abbreviation, {abbreviation})
    for comp in event.get("competitions", []):
        for competitor in comp.get("competitors", []):
            team = competitor.get("team") or {}
            if str(team.get("abbreviation", "")).upper() in wanted:
                return True
    return False

def relevant(events, prefs=None):
    prefs = prefs or preferences()
    mode = prefs.get("mode", "all")
    favorite = prefs.get("favorite_team", "SJ")
    now = datetime.now(timezone.utc)
    result = []

    for event in events:
        try:
            start = event_time(event)
            state = event["status"]["type"]["state"]
        except (KeyError, ValueError, TypeError):
            continue

        if mode == "only" and not has_team(event, favorite):
            continue

        if state == "in":
            result.append(event)
        elif state == "pre" and now <= start <= now + timedelta(days=15):
            result.append(event)
        elif state == "post" and now - timedelta(days=2) <= start <= now:
            result.append(event)

    if mode == "only":
        live = [e for e in result if e["status"]["type"]["state"] == "in"]
        upcoming = sorted(
            (e for e in result if e["status"]["type"]["state"] == "pre"),
            key=event_time
        )
        finals = sorted(
            (e for e in result if e["status"]["type"]["state"] == "post"),
            key=event_time, reverse=True
        )
        # Show live first, then the next game, then the latest final.
        return live or upcoming[:1] or finals[:1]

    return sorted(result, key=priority)

def fetch_events(prefs=None):
    prefs = prefs or preferences()
    now = datetime.now(PT)
    events = {}
    horizon = 15 if prefs.get("mode") == "only" else 3

    for offset in range(-2, horizon + 1):
        day = now + timedelta(days=offset)
        try:
            data = json.loads(fetch(API + "&dates=" + day.strftime("%Y%m%d")))
            for event in data.get("events", []):
                if event.get("id"):
                    events[str(event["id"])] = event
        except Exception as exc:
            print("NHL fetch failed:", day.date(), exc)

    return relevant(list(events.values()), prefs)

class NHLRotation:
    def __init__(self):
        self.events = []
        self.current_id = None
        self.last_schedule_fetch = 0
        self.last_live_fetch = 0
        self.last_rotate = time.monotonic()
        self.last_preferences = None

    def tick(self):
        now = time.monotonic()
        prefs = preferences()
        signature = json.dumps(prefs, sort_keys=True)

        if signature != self.last_preferences:
            self.events = []
            self.current_id = None
            self.last_schedule_fetch = 0
            self.last_preferences = signature

        if not self.events or now - self.last_schedule_fetch >= 300:
            try:
                self.events = fetch_events(prefs)
            except Exception as exc:
                print("NHL schedule error:", exc)
            self.last_schedule_fetch = now

        live = [
            e for e in self.events
            if e.get("status", {}).get("type", {}).get("state") == "in"
        ]

        if live and now - self.last_live_fetch >= 5:
            try:
                days = {
                    event_time(e).astimezone(PT).strftime("%Y%m%d")
                    for e in live
                }
                updates = {}
                for day in days:
                    data = json.loads(fetch(API + "&dates=" + day))
                    for event in data.get("events", []):
                        updates[str(event["id"])] = event

                self.events = [
                    updates.get(str(e["id"]), e) for e in self.events
                ]
            except Exception as exc:
                print("NHL live update error:", exc)
            self.last_live_fetch = now

        self.events = relevant(self.events, prefs)
        if not self.events:
            return None

        ids = [str(e["id"]) for e in self.events]
        if self.current_id not in ids:
            self.current_id = ids[0]
            self.last_rotate = now
        else:
            current = next(e for e in self.events
                           if str(e["id"]) == self.current_id)
            favorite = has_team(current, prefs.get("favorite_team", "SJ"))
            duration = (
                int(prefs.get("favorite_seconds", 90))
                if prefs.get("mode") == "prefer" and favorite
                else int(prefs.get("other_seconds", 30))
            )
            if now - self.last_rotate >= duration:
                self.current_id = ids[(ids.index(self.current_id) + 1) % len(ids)]
                self.last_rotate = now

        return next(e for e in self.events
                    if str(e["id"]) == self.current_id)
