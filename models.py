from dataclasses import dataclass
from typing import Optional
from datetime import datetime


@dataclass
class Team:
    name: str
    abbr: str
    score: Optional[int] = None
    asset_path: Optional[str] = None


@dataclass
class Game:
    league: str
    home: Team
    away: Team
    status: str          # pre, in, post
    detail: str          # FT, 67', Q3 8:22, 3:00P, etc.
    start_time: datetime
    group: Optional[str] = None
    completed_time: Optional[datetime] = None

    def includes_team(self, abbr: str) -> bool:
        abbr = abbr.upper()
        return self.home.abbr.upper() == abbr or self.away.abbr.upper() == abbr
