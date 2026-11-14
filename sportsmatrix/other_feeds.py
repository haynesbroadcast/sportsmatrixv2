"""Scoreboard feeds for additional SportsMatrix leagues.

ESPN site scoreboards share an event schema. The PWHL is supplied by its
public HockeyTech / LeagueStat scorebar rather than pretending an ESPN
hockey/PWHL endpoint exists.
"""
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import requests

PT = ZoneInfo("America/Los_Angeles")
ESPN_PATHS = {
    "nba": "basketball/nba",
    "wnba": "basketball/wnba",
    "mlb": "baseball/mlb",
    "mls": "soccer/usa.1",
    "nwsl": "soccer/usa.nwsl",
    "epl": "soccer/eng.1",
}
ESPN_BASE = "https://site.api.espn.com/apis/site/v2/sports/"


def fetch_events(league):
    if league not in ESPN_PATHS:
        raise ValueError(f"Unknown league: {league}")
    now = datetime.now(PT)
    # Range queries provide a recent result or upcoming games in off-hours
    # while making only one network request per worker refresh.
    start = (now - timedelta(days=2)).strftime("%Y%m%d")
    end = (now + timedelta(days=21 if league == "epl" else 8)).strftime("%Y%m%d")
    response = requests.get(
        f"{ESPN_BASE}{ESPN_PATHS[league]}/scoreboard",
        params={"dates": f"{start}-{end}", "limit": 200},
        headers={"User-Agent": "SportsMatrixV2/0.11"},
        timeout=15,
    )
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict) or not isinstance(payload.get("events", []), list):
        raise ValueError(f"{league} scoreboard returned an invalid event payload")
    return prioritize(payload["events"], now)


def prioritize(events, now=None):
    """Keep live games first, then upcoming, then recent finals."""
    now = now or datetime.now(PT)
    start_recent = now - timedelta(days=2)
    filtered = []
    for event in events:
        comps = event.get("competitions") or []
        if not comps or len(comps[0].get("competitors") or []) < 2:
            continue
        state = event.get("status", {}).get("type", {}).get("state")
        try:
            when = datetime.fromisoformat(event["date"].replace("Z", "+00:00")).astimezone(PT)
        except (KeyError, ValueError, TypeError):
            continue
        if state == "in" or (state == "pre" and when >= now - timedelta(hours=4)) or (state == "post" and when >= start_recent):
            filtered.append(event)
    order = {"in": 0, "pre": 1, "post": 2}
    return sorted(filtered, key=lambda e: (order.get(e.get("status", {}).get("type", {}).get("state"), 3),
                                            e.get("date", "")))


