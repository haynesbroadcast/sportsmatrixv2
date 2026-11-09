from datetime import datetime, timedelta, time
from zoneinfo import ZoneInfo


def choose_featured_game(games, settings):
    """
    Selection rules:
    1. Favorite live game.
    2. Any live game.
    3. Recently final favorite game, held for final_hold_minutes.
    4. Recently final any game, held for final_hold_minutes.
    5. Favorite next game.
    6. Any next game.
    """
    tz = ZoneInfo(settings.get("timezone", "America/Los_Angeles"))
    now = datetime.now(tz)
    favorite = settings.get("favorite_team", "").upper()
    final_hold = timedelta(minutes=int(settings.get("final_hold_minutes", 15)))

    games = sorted(games, key=lambda g: g.start_time.astimezone(tz))

    live = [g for g in games if g.status == "in"]
    fav_live = [g for g in live if favorite and g.includes_team(favorite)]
    if fav_live:
        return fav_live[0], "live"
    if live:
        return live[0], "live"

    upcoming = [g for g in games if g.status == "pre" and g.start_time.astimezone(tz) >= now - timedelta(minutes=15)]
    if upcoming:
        return upcoming[0], "countdown"

    recent_final = []
    for g in games:
        if g.status == "post" and g.completed_time:
            end = g.completed_time.astimezone(tz)
            if now - end <= final_hold:
                recent_final.append(g)

    fav_recent_final = [g for g in recent_final if favorite and g.includes_team(favorite)]
    if fav_recent_final:
        return fav_recent_final[0], "final_hold"
    if recent_final:
        return recent_final[-1], "final_hold"

    upcoming = [g for g in games if g.status == "pre" and g.start_time.astimezone(tz) >= now - timedelta(minutes=15)]
    # Only prioritize a favorite upcoming game if it is reasonably soon.
    # Otherwise, show the next chronological match.
    fav_upcoming = [
        g for g in upcoming
        if favorite
        and g.includes_team(favorite)
        and g.start_time.astimezone(tz) - now <= timedelta(hours=6)
    ]

    if fav_upcoming:
        game = fav_upcoming[0]
    elif upcoming:
        game = upcoming[0]
    else:
        return games[-1] if games else None, "fallback"

    start_local = game.start_time.astimezone(tz)
    if start_local.date() > now.date():
        morning_hour = int(settings.get("next_day_countdown_start_hour", 7))
        morning = datetime.combine(start_local.date(), time(hour=morning_hour), tzinfo=tz)

        # Before morning, still return the next game, but renderer should show simple "NEXT" state.
        if now < morning:
            return game, "next_day_wait"

    return game, "countdown"
