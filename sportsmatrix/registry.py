"""Single source of truth for leagues and hardware profiles."""
from dataclasses import dataclass

@dataclass(frozen=True)
class League:
    key: str
    label: str
    sport: str
    renderer: str
    favorite_kind: str = "team"
    enabled: bool = True

LEAGUES = {
    x.key: x for x in (
        League("nhl", "NHL", "hockey", "nhl"),
        League("nfl", "NFL", "football", "nfl"),
        League("cfb", "College Football", "football", "cfb"),
        League("golf", "PGA Golf", "golf", "golf", "golfer"),
        League("nba", "NBA", "basketball", "basketball", enabled=True),
        League("wnba", "WNBA", "basketball", "basketball", enabled=True),
        League("nwsl", "NWSL", "soccer", "soccer", enabled=True),
        League("epl", "Premier League", "soccer", "soccer", enabled=True),
        League("mls", "MLS", "soccer", "soccer", enabled=True),
        League("pwhl", "PWHL", "hockey", "hockey", enabled=True),
        League("pll", "PLL Lacrosse", "lacrosse", "lacrosse", enabled=True),
        League("mlb", "MLB", "baseball", "baseball", enabled=True),
    )
}
PROFILES = {"compact_64x32": (64, 32), "enhanced_128x64": (128, 64)}

def supported():
    return {key: league for key, league in LEAGUES.items() if league.enabled}
