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
    "pll": "lacrosse/pll",
}
ESPN_BASE = "https://site.api.espn.com/apis/site/v2/sports/"
PWHL_URL = "https://lscluster.hockeytech.com/feed/index.php"
# Public read-only key used by the PWHL site / HockeyTech stats.
PWHL_KEY = "446521baf8c38984"


def fetch_events(league):
    if league == "pwhl":
        return fetch_pwhl()
    if league not in ESPN_PATHS:
        raise ValueError(f"Unknown league: {league}")
    now = datetime.now(PT)
    # Range queries provide a recent result or upcoming games in off-hours
    # while making only one network request per worker refresh.
    start = (now - timedelta(days=2)).strftime("%Y%m%d")
    end = (now + timedelta(days=8)).strftime("%Y%m%d")
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


def _name(team):
    if isinstance(team, dict):
        return team.get("name") or team.get("nickname") or team.get("city") or team.get("abbreviation") or "TEAM"
    return str(team or "TEAM")


def _hockeytech_team(raw, side):
    nested = raw.get(side + "_team")
    if isinstance(nested, dict):
        name = _name(nested)
        ident = nested.get("id") or nested.get("team_id") or name
        abbr = nested.get("abbreviation") or nested.get("code") or nested.get("short_name") or name[:3]
        logo = nested.get("logo") or nested.get("logo_url")
    else:
        name = raw.get(side + "_team_name") or raw.get(side + "_name") or str(nested or side.upper())
        ident = raw.get(side + "_team_id") or name
        abbr = raw.get(side + "_team_code") or name[:3]
        logo = raw.get(side + "_team_logo")
    return {"id": str(ident), "abbreviation": str(abbr).upper()[:5],
            "displayName": name, "logo": logo if isinstance(logo, str) and logo.startswith("https://") else None}


def parse_pwhl(payload):
    """Normalize HockeyTech scorebar events into the ESPN event shape.

    Only use supplied information; unknown clock, shots and score are left
    unknown, not invented. HockeyTech fields vary between season releases.
    """
    if not isinstance(payload, dict):
        raise ValueError("Invalid HockeyTech scorebar response")
    content = payload.get("SiteKit") or payload.get("sitekit") or payload
    games = (content.get("Scorebar") or content.get("scorebar") or
             content.get("games") or []) if isinstance(content, dict) else []
    if isinstance(games, dict):
        games = games.get("games") or games.get("data") or []
    events = []
    for item in games:
        if not isinstance(item, dict):
            continue
        ident = item.get("ID") or item.get("id") or item.get("game_id")
        if not ident:
            continue
        home = _hockeytech_team(item, "home")
        away = _hockeytech_team(item, "visiting")
        if away["displayName"] == "VISITING":
            away = _hockeytech_team(item, "away")
        status = str(item.get("GameStatus") or item.get("game_status") or item.get("status") or "1")
        state = "post" if status in ("4", "5", "Final", "final") else "in" if status in ("2", "3", "In Progress", "Live") else "pre"
        raw_date = item.get("Date") or item.get("date") or item.get("game_date")
        raw_time = item.get("ScheduledTime") or item.get("scheduled_time") or item.get("time") or "00:00"
        if not raw_date:
            continue
        raw_date = str(raw_date)
        try:
            if "T" in raw_date:
                when = datetime.fromisoformat(raw_date.replace("Z", "+00:00"))
            else:
                when = datetime.fromisoformat(raw_date[:10] + "T" + str(raw_time)[:5])
            if when.tzinfo is None:
                when = when.replace(tzinfo=PT)
        except ValueError:
            continue
        def score(side):
            value = item.get(side + "_goal_count")
            if value is None:
                value = item.get(side + "_score")
            return None if value is None or str(value) == "" else str(value)
        teams = [
            {"homeAway": "away", "team": away, "score": score("visiting") or score("away")},
            {"homeAway": "home", "team": home, "score": score("home")},
        ]
        events.append({
            "id": "pwhl_" + str(ident),
            "date": when.isoformat(),
            "name": f"{away['displayName']} at {home['displayName']}",
            "status": {"type": {"state": state,
                                "shortDetail": "FINAL" if state == "post" else ("LIVE" if state == "in" else "SCHEDULED")},
                       "period": item.get("Period") or item.get("period") or 0,
                       "displayClock": item.get("Clock") or item.get("clock") or ""},
            "competitions": [{"competitors": teams}],
        })
    return events


def fetch_pwhl():
    response = requests.get(
        PWHL_URL,
        params={"feed": "modulekit", "view": "scorebar", "key": PWHL_KEY,
                "client_code": "pwhl", "numberofdaysback": 2,
                "numberofdaysahead": 8, "lang": "en", "fmt": "json"},
        headers={"User-Agent": "SportsMatrixV2/0.11"},
        timeout=15,
    )
    response.raise_for_status()
    return prioritize(parse_pwhl(response.json()))
