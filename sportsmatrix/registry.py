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
        League("nba", "NBA", "basketball", "basketball", enabled=False),
        League("wnba", "WNBA", "basketball", "basketball", enabled=False),
        League("nwsl", "NWSL", "soccer", "soccer", enabled=False),
        League("epl", "Premier League", "soccer", "soccer", enabled=False),
        League("mls", "MLS", "soccer", "soccer", enabled=False),
        League("pwhl", "PWHL", "hockey", "hockey", enabled=False),
        League("pll", "PLL Lacrosse", "lacrosse", "lacrosse", enabled=False),
        League("mlb", "MLB", "baseball", "baseball", enabled=False),
    )
}
PROFILES = {"compact_64x32": (64, 32), "enhanced_128x64": (128, 64)}

def supported():
    return {key: league for key, league in LEAGUES.items() if league.enabled}
