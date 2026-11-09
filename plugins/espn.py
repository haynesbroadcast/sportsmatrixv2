from datetime import datetime, timezone
from dateutil import parser as dateparser
import requests
from models import Game, Team


ENDPOINTS = {
    "worldcup": "https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/scoreboard",
    "mlb": "https://site.api.espn.com/apis/site/v2/sports/baseball/mlb/scoreboard",
    "nfl": "https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard",
    "nhl": "https://site.api.espn.com/apis/site/v2/sports/hockey/nhl/scoreboard",
    "nba": "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard",
}


def fetch_games(league: str):
    params = {}

    if league == "worldcup":
        from datetime import timedelta
        now = datetime.now(timezone.utc)
        start = now - timedelta(days=1)
        end = now + timedelta(days=8)
        params["dates"] = f"{start.strftime('%Y%m%d')}-{end.strftime('%Y%m%d')}"

    response = requests.get(ENDPOINTS[league], params=params, timeout=15)
    response.raise_for_status()
    return parse_games(response.json(), league)

def _safe_int(value):
    try:
        return int(value)
    except Exception:
        return None


def _team_from_competitor(raw, league):
    team = raw.get("team", {})
    abbr = (team.get("abbreviation") or team.get("shortDisplayName") or "???").upper()

    asset_folder = "flags" if league == "worldcup" else f"logos/{league}"
    return Team(
        name=team.get("displayName") or abbr,
        abbr=abbr,
        score=_safe_int(raw.get("score")),
        asset_path=f"assets/{asset_folder}/{abbr}.png",
    )


def _group_from_event(event):
    # ESPN often places group/competition notes in different locations.
    name = event.get("name", "")
    season = event.get("season", {})
    note = event.get("shortName", "")

    for item in [name, note, str(season)]:
        if "Group" in item:
            # Good enough for MVP; we can make this smarter later.
            parts = item.split("Group")
            if len(parts) > 1:
                return "Group " + parts[1].strip()[:1]
    return None


def parse_games(payload, league):
    games = []
    now = datetime.now(timezone.utc)

    for event in payload.get("events", []):
        comps = event.get("competitions", [])
        if not comps:
            continue

        comp = comps[0]
        competitors = comp.get("competitors", [])
        if len(competitors) < 2:
            continue

        home_raw = next((c for c in competitors if c.get("homeAway") == "home"), competitors[0])
        away_raw = next((c for c in competitors if c.get("homeAway") == "away"), competitors[1])

        status_type = comp.get("status", {}).get("type", {})
        state = status_type.get("state", "pre")
        detail = status_type.get("shortDetail") or status_type.get("detail") or status_type.get("description") or state

        start_time = dateparser.parse(event["date"])

        # ESPN does not reliably provide the actual final whistle timestamp.
        # Do not fake it with "now", or final-hold will never expire.
        completed_time = None

        games.append(Game(
            league=league,
            home=_team_from_competitor(home_raw, league),
            away=_team_from_competitor(away_raw, league),
            status=state,
            detail=detail,
            start_time=start_time,
            group=_group_from_event(event),
            completed_time=completed_time,
        ))

    return games



def fetch_golf_leaderboard():
    import requests
    from datetime import datetime, timedelta, timezone
    from zoneinfo import ZoneInfo

    PT = ZoneInfo("America/Los_Angeles")
    url = "https://site.api.espn.com/apis/site/v2/sports/golf/pga/scoreboard"
    data = requests.get(url, timeout=15).json()
    events = data.get("events", [])

    if not events:
        return {"title": "GOLF", "players": [], "live": False}

    event = next(
        (e for e in events if e.get("status", {}).get("type", {}).get("state") == "in"),
        events[0]
    )
    comp = (event.get("competitions") or [{}])[0]
    state = event.get("status", {}).get("type", {}).get("state", "")
    competitors = sorted(
        comp.get("competitors", []),
        key=lambda c: int(c.get("order") or 9999)
    )

    now = datetime.now(timezone.utc)
    players = []
    previous_score = None
    previous_position = 0

    def tee_time(round_data):
        # Only use explicit future round date fields.
        for key in ("startDate", "teeTime", "date"):
            value = round_data.get(key)
            if not isinstance(value, str):
                continue
            try:
                dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
                if dt.tzinfo is None:
                    continue
                if now <= dt <= now + timedelta(days=3):
                    return dt.astimezone(PT).strftime("%-I:%M%p").lower()
            except ValueError:
                pass
        return None

    for index, c in enumerate(competitors[:16]):
        athlete = c.get("athlete") or {}
        name = athlete.get("shortName") or athlete.get("displayName") or "Player"
        if "." not in name and " " in name:
            parts = name.split()
            name = parts[0][0] + ". " + parts[-1]

        score = str(c.get("score", "E"))
        rounds = c.get("linescores") or []
        latest = rounds[-1] if rounds else {}
        holes = latest.get("linescores") or []
        completed = sum(1 for h in holes if h.get("value") is not None)

        upcoming_tee = None
        if completed == 0:
            upcoming_tee = tee_time(latest)

        if completed >= 18:
            thru = "F"
        elif completed > 0:
            thru = str(completed)
        elif upcoming_tee:
            thru = upcoming_tee
        elif any(r.get("value") is not None for r in rounds[:-1]):
            thru = "F"
        else:
            thru = "--"

        if score == previous_score:
            position = "T" + str(previous_position)
        else:
            previous_position = index + 1
            position = str(previous_position)
        previous_score = score

        players.append({
            "name": name.upper(),
            "position": position,
            "score": score,
            "thru": thru,
            "round": latest.get("period", len(rounds)),
        })

    for i in range(len(players) - 1):
        if players[i]["score"] == players[i + 1]["score"]:
            if not players[i]["position"].startswith("T"):
                players[i]["position"] = "T" + players[i]["position"]

    return {
        "title": event.get("shortName") or event.get("name") or "GOLF",
        "players": players,
        "live": state == "in",
        "round": max((p["round"] or 0 for p in players), default=0),
    }
