"""CFB weekend paging regression: Friday games must not hide Saturday."""
import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch
from zoneinfo import ZoneInfo

from sportsmatrix.selection import cfb_weekend_pages, daily_matchup_pages, ranked_cfb_games
from sportsmatrix.worker import VirtualWorker

PT = ZoneInfo("America/Los_Angeles")


def game(ident, day=20, hour=18, minute=0, state="pre",
         rank=None, bowl=False):
    teams = [
        {"homeAway": "away", "team": {"id": "1"}},
        {"homeAway": "home", "team": {"id": "2"}},
    ]
    if rank is not None:
        teams[0]["curatedRank"] = {"current": rank}
    return {
        "id": ident,
        "date": datetime(2026, 11, day, hour, minute, tzinfo=PT).isoformat(),
        "status": {"type": {"state": state}},
        "season": {"type": 3 if bowl else 2},
        "competitions": [{"competitors": teams}],
    }


class CfbWeekendTests(unittest.TestCase):
    def test_friday_includes_saturday_ranked_games(self):
        events = [
            game("oregon-michigan", day=20, rank=6),
            game("sat-1", day=21, hour=12, rank=2),
            game("sat-2", day=21, hour=12, minute=15, rank=13),
            game("sat-3", day=21, hour=12, minute=30, rank=25),
            game("unranked", day=21, hour=15),
        ]
        now = datetime(2026, 11, 20, 19, tzinfo=PT)
        pages = cfb_weekend_pages(ranked_cfb_games(events), now)
        self.assertEqual(len(pages), 2)
        self.assertEqual(pages[0]["events"][0]["id"], "oregon-michigan")
        self.assertEqual(pages[1]["kind"], "slate")
        self.assertEqual(
            [e["id"] for e in pages[1]["events"]],
            ["sat-1", "sat-2", "sat-3"])
        self.assertEqual(len(daily_matchup_pages(
            ranked_cfb_games(events), now)), 1)

    def test_saturday_drops_friday_but_keeps_sunday(self):
        events = [game("fri", day=20, rank=1),
                  game("sat", day=21, rank=2),
                  game("sun", day=22, rank=3)]
        pages = cfb_weekend_pages(
            ranked_cfb_games(events),
            datetime(2026, 11, 21, 9, tzinfo=PT))
        self.assertEqual([p["events"][0]["id"] for p in pages],
                         ["sat", "sun"])

    def test_live_scores_keep_standalone_pages(self):
        events = [game("live", day=21, hour=12, state="in", rank=5),
                  game("future", day=21, hour=12, minute=15, rank=8)]
        pages = cfb_weekend_pages(
            ranked_cfb_games(events),
            datetime(2026, 11, 21, 12, tzinfo=PT))
        self.assertEqual([p["kind"] for p in pages], ["game", "game"])

    def test_unranked_bowl_included_even_in_midweek(self):
        # The week window begins Tuesday and includes midweek bowl dates.
        events = [game("tuesday-bowl", day=24, bowl=True),
                  game("wednesday-bowl", day=25, bowl=True),
                  game("regular-unranked", day=25)]
        pages = cfb_weekend_pages(
            ranked_cfb_games(events),
            datetime(2026, 11, 24, 9, tzinfo=PT))
        self.assertEqual([p["events"][0]["id"] for p in pages],
                         ["tuesday-bowl", "wednesday-bowl"])

    def test_worker_uses_cfb_weekend_not_daily_pages(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = Path(tmp) / "settings.json"
            config.write_text(json.dumps({"league": "cfb", "power": "on",
                                          "profile": "enhanced_128x64"}))
            worker = VirtualWorker(config)
            eligible = game("ranked", rank=7)
            ignored = game("unranked")
            pages = [{"kind": "game", "events": [eligible], "page": 0,
                      "key": ("game", "ranked")}]
            with patch.object(worker, "fetch",
                              return_value=[eligible, ignored]), \
                 patch.object(worker, "render",
                              return_value="enhanced_128x64") as render, \
                 patch("sportsmatrix.selection.cfb_weekend_pages",
                       return_value=pages) as week, \
                 patch("sportsmatrix.selection.daily_matchup_pages") as daily, \
                 patch("sportsmatrix.worker.STATUS", Path(tmp) / "state.json"), \
                 patch("sportsmatrix.worker.time.monotonic", return_value=100):
                result = worker.tick()
            self.assertEqual(result["event_id"], "cfb-weekend-1-of-1")
            self.assertEqual([e["id"] for e in week.call_args.args[0]],
                             ["ranked"])
            daily.assert_not_called()
            self.assertEqual(render.call_args.kwargs["carousel"], (0, 1))


if __name__ == "__main__":
    unittest.main()
