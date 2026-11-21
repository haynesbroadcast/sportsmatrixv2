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
    finals = [e for e in events if state(e) == "post" and start(e)
              and start(e).astimezone(ZoneInfo("America/Los_Angeles")).date() == local_day]
    # After the last Sunday window, prefer today's results to next week's games.
    if finals and (not upcoming or
                   start(upcoming[0]).astimezone(ZoneInfo("America/Los_Angeles")).date() > local_day):
        return finals
    if upcoming:
        first = start(upcoming[0])
        # Games with kickoffs within 45 minutes belong to the same block.
        return [e for e in upcoming if start(e) <= first + timedelta(minutes=45)]

    finals = [e for e in events if state(e) == "post" and start(e)
              and start(e).astimezone(ZoneInfo("America/Los_Angeles")).date() == local_day]
    return finals or list(events)


def nfl_weekend_pages(events, now=None):
    """Chronological NFL carousel from today through the coming Monday (PT).

    Tuesday begins the next NFL viewing week. Past calendar days never appear,
    even when ESPN still reports their games as completed. Games sharing a
    local kickoff window (within 45 minutes) use 3-up pregame slate pages.
    Single games, and any window with live/final games, use full-game pages
    to preserve scores and situation details.
    """
    from datetime import timedelta
    from zoneinfo import ZoneInfo

    pacific = ZoneInfo("America/Los_Angeles")
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    today = now.astimezone(pacific).date()
    # Monday is weekday 0. On Monday show Monday only; on Tuesday begin
    # the upcoming Thu/Fri/Sun/Mon sequence, including holiday exceptions.
    end_day = today + timedelta(days=(7 - today.weekday()) % 7)

    ordered = []
    for event in events:
        try:
            start = datetime.fromisoformat(event["date"].replace("Z", "+00:00"))
            local_start = start.astimezone(pacific)
            state = event["status"]["type"]["state"]
        except (KeyError, ValueError, TypeError, AttributeError):
            continue
        if today <= local_start.date() <= end_day and state in ("pre", "in", "post"):
            ordered.append((local_start, event))
    ordered.sort(key=lambda pair: (pair[0], str(pair[1].get("id", ""))))

    groups = []
    for start, event in ordered:
        if (not groups or start.date() != groups[-1][0].date()
                or start - groups[-1][0] > timedelta(minutes=45)):
            groups.append((start, [event]))
        else:
            groups[-1][1].append(event)

    pages = []
    for start, group in groups:
        # A live game must never appear as a pregame graphic without its score.
        if len(group) == 1 or any(
                e["status"]["type"]["state"] != "pre" for e in group):
            for event in group:
                pages.append({"kind": "game", "events": [event], "page": 0,
                              "key": ("game", str(event.get("id")))})
        else:
            for index in range((len(group) + 2) // 3):
                chunk = group[index * 3:(index + 1) * 3]
                if len(chunk) == 1:
                    # A fourth or seventh game deserves a full screen rather
                    # than a nearly empty three-row slate.
                    event = chunk[0]
                    pages.append({"kind": "game", "events": [event], "page": 0,
                                  "key": ("game", str(event.get("id")))})
                else:
                    pages.append({"kind": "slate", "events": group, "page": index,
                                  "key": ("slate", tuple(str(e.get("id")) for e in group),
                                          index)})
    return pages
