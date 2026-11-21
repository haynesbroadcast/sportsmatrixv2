"""CFB eligibility: Top 25 matchup OR any bowl/postseason game."""
import unittest
from datetime import datetime
from zoneinfo import ZoneInfo

from sportsmatrix.selection import ranked_cfb_games
from cfb_runtime import relevant

PT = ZoneInfo("America/Los_Angeles")


def game(ident, away_rank=None, home_rank=None, postseason=False):
    teams = [
        {"homeAway": "away", "team": {"id": "1"}},
        {"homeAway": "home", "team": {"id": "2"}},
    ]
    for team, n in zip(teams, (away_rank, home_rank)):
        if n is not None:
            team["curatedRank"] = {"current": n}
    return {
        "id": ident,
        "date": "2026-12-19T16:00:00-08:00",
        "status": {"type": {"state": "pre"}},
        "season": {"type": 3 if postseason else 2},
        "competitions": [{"competitors": teams}],
    }


class CfbEligibilityTests(unittest.TestCase):
    def test_either_team_ranked_qualifies(self):
        games = [game("away", away_rank=3),
                 game("home", home_rank=25),
                 game("both", away_rank=4, home_rank=7),
                 game("unranked"),
                 game("not-top25", home_rank=26)]
        self.assertEqual([g["id"] for g in ranked_cfb_games(games)],
                         ["away", "home", "both"])

    def test_all_bowls_even_with_unranked_teams(self):
        games = [game("unranked-bowl", postseason=True),
                 game("playoff", away_rank=2, postseason=True),
                 game("ordinary-unranked")]
        self.assertEqual([g["id"] for g in ranked_cfb_games(games)],
                         ["unranked-bowl", "playoff"])

    def test_missing_rank_or_season_does_not_invent_exception(self):
        missing = game("missing")
        missing.pop("season")
        self.assertEqual(ranked_cfb_games([missing]), [])

    def test_relevant_no_longer_truncates_to_ten(self):
        games = [game(str(i), away_rank=25) for i in range(14)]
        now = datetime(2026, 12, 19, 10, tzinfo=PT)
        self.assertEqual(len(relevant(games, now)), 14)

    def test_unranked_bowls_survive_source_filter(self):
        games = [game("bowl", postseason=True),
                 game("regular", postseason=False)]
        now = datetime(2026, 12, 19, 10, tzinfo=PT)
        self.assertEqual([g["id"] for g in relevant(games, now)], ["bowl"])


if __name__ == "__main__":
    unittest.main()
