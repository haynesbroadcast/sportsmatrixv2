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
                # Even a lone overflow matchup keeps the slate visual
                # treatment. Only genuinely standalone windows go full-screen.
                pages.append({"kind": "slate", "events": group, "page": index,
                              "key": ("slate", tuple(str(e.get("id")) for e in group),
                                      index)})
    return pages


def daily_matchup_pages(events, now=None):
    """Non-NFL team sports: focus on the active local day, or next game day.

    Unlike the NFL's Thursday–Monday broadcast week, NBA/NHL/CFB/soccer
    calendars have different rhythms. Show all of today's games (including
    completed games), then fall forward to the next scheduled game day.
    Never mix unrelated calendar days into one slate. Games within 45
    minutes of a window start use 3-up pages while still pregame; live/final
    games keep their dedicated score-first screens.
    """
    from datetime import timezone, timedelta
    from zoneinfo import ZoneInfo

    pacific = ZoneInfo("America/Los_Angeles")
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    today = now.astimezone(pacific).date()
    valid = []
    for event in events:
        try:
            start = datetime.fromisoformat(event["date"].replace("Z", "+00:00"))
            local = start.astimezone(pacific)
            state = event["status"]["type"]["state"]
            if state not in ("pre", "in", "post"):
                continue
        except (KeyError, ValueError, TypeError, AttributeError):
            continue
        valid.append((local, state, event))
    if not valid:
        return []

    # An overnight game is still relevant while live, even if it started
    # before local midnight. Today's games win over a future schedule.
    active = [(t, e) for t, state, e in valid
              if t.date() == today or state == "in"]
    if not active:
        future_days = [t.date() for t, state, _ in valid
                       if state == "pre" and t.date() > today]
        if not future_days:
            return []
        focus = min(future_days)
        active = [(t, e) for t, state, e in valid
                  if t.date() == focus and state == "pre"]

    active.sort(key=lambda pair: (pair[0], str(pair[1].get("id", ""))))
    groups = []
    for start, event in active:
        if (not groups or start.date() != groups[-1][0].date()
                or start - groups[-1][0] > timedelta(minutes=45)):
            groups.append((start, [event]))
        else:
            groups[-1][1].append(event)

    pages = []
    for _, group in groups:
        if len(group) == 1 or any(
                e["status"]["type"]["state"] != "pre" for e in group):
            for event in group:
                pages.append({"kind": "game", "events": [event], "page": 0,
                              "key": ("game", str(event.get("id")))})
        else:
            signature = tuple(str(e.get("id")) for e in group)
            for index in range((len(group) + 2) // 3):
                pages.append({"kind": "slate", "events": group, "page": index,
                              "key": ("slate", signature, index)})
    return pages


def ranked_cfb_games(events):
    """Only CFB matchups with at least one ESPN Top 25 team.

    No rivalry, bowl, championship, conference or upset exceptions.
    Missing/invalid ranks do not qualify.
    """
    from render.cfb_v2 import rank
    return [
        event for event in events
        if any(
            rank(competitor) is not None
            for competition in event.get("competitions", [])
            for competitor in competition.get("competitors", [])
        )
    ]
