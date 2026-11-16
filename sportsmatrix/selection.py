"""Reusable favorite-team selection and duration policy."""
from datetime import datetime, timezone

def is_favorite(event, favorite):
    if not favorite: return False
    aliases = {"SJ": {"SJ", "SJS"}, "SJS": {"SJ", "SJS"}}
    wanted = aliases.get(favorite.upper(), {favorite.upper()})
    return any(str(c.get("team",{}).get("abbreviation", "")).upper() in wanted
               for competition in event.get("competitions", [])
               for c in competition.get("competitors", []))

def choose(events, prefs):
    mode = prefs.get("mode", "all")
    favorite = prefs.get("favorite_team", "")
    if mode != "only" or not favorite:
        return list(events)
    matches = [e for e in events if is_favorite(e, favorite)]
    live = [e for e in matches if e.get("status",{}).get("type",{}).get("state") == "in"]
    future = [e for e in matches if e.get("status",{}).get("type",{}).get("state") == "pre"]
    finals = [e for e in matches if e.get("status",{}).get("type",{}).get("state") == "post"]
    future.sort(key=lambda e: e.get("date", ""))
    finals.sort(key=lambda e: e.get("date", ""), reverse=True)
    return live or future[:1] or finals[:1]

def duration(event, prefs):
    if prefs.get("mode") == "prefer" and is_favorite(event, prefs.get("favorite_team", "")):
        return prefs.get("favorite_seconds", 90)
    return prefs.get("other_seconds", 30)


def nfl_broadcast_window(events, now=None):
    """Only rotate the current NFL broadcast block, not the whole week.

    Live games win. Between windows, show the next kickoff group. After
    the day's last game, retain today's finals instead of next Sunday.
    """
    from datetime import timedelta
    from zoneinfo import ZoneInfo

    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    local_day = now.astimezone(ZoneInfo("America/Los_Angeles")).date()

    def start(event):
        try:
            return datetime.fromisoformat(event["date"].replace("Z", "+00:00"))
        except (KeyError, ValueError, TypeError):
            return None

    def state(event):
        return event.get("status", {}).get("type", {}).get("state")

    live = [e for e in events if state(e) == "in"]
    if live:
        return live

    upcoming = sorted(
        (e for e in events if state(e) == "pre" and start(e) and start(e) >= now),
        key=lambda e: start(e),
    )
    if upcoming:
        first = start(upcoming[0])
        # Games with kickoffs within 45 minutes belong to the same block.
        return [e for e in upcoming if start(e) <= first + timedelta(minutes=45)]

    finals = [e for e in events if state(e) == "post" and start(e)
              and start(e).astimezone(ZoneInfo("America/Los_Angeles")).date() == local_day]
    return finals or list(events)
