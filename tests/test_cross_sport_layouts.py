"""Cross-sport v0.18 layout and daily-rotation regression tests."""
import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch
from zoneinfo import ZoneInfo

from PIL import Image, ImageDraw

from render.matchup_slate import LEAGUES, render_feature, render_slate
from render.golf import render_golf
from sportsmatrix.selection import daily_matchup_pages
from sportsmatrix.worker import VirtualWorker

PT = ZoneInfo("America/Los_Angeles")


def event(ident, day=20, hour=19, minute=0, state="pre"):
    start = datetime(2026, 11, day, hour, minute, tzinfo=PT)
    return {"id": ident, "name": "Test game",
            "date": start.isoformat(),
            "status": {"type": {"state": state}, "period": 2,
                       "displayClock": "05:42"},
            "competitions": [{"competitors": [
                {"homeAway": "away", "score": "2",
                 "team": {"id": "1", "abbreviation": "AWY",
                          "color": "00338D"}},
                {"homeAway": "home", "score": "3",
                 "team": {"id": "2", "abbreviation": "HME",
                          "color": "008E97"}}]}]}


def dark_logo():
    image = Image.new("RGBA", (18, 18), (0, 0, 0, 0))
    ImageDraw.Draw(image).ellipse((2, 2, 15, 15),
                                  fill=(7, 22, 50, 255))
    return image


class DailySelectionTests(unittest.TestCase):
    def test_today_then_next_game_day_not_full_week(self):
        events = [event(str(i), hour=19, minute=i * 10)
                  for i in range(4)]
        events += [event("late", hour=21),
                   event("tomorrow", day=21, hour=13)]
        now = datetime(2026, 11, 20, 10, tzinfo=PT)
        pages = daily_matchup_pages(events, now)
        self.assertEqual([p["kind"] for p in pages],
                         ["slate", "slate", "game"])
        self.assertEqual(pages[1]["page"], 1)
        self.assertEqual(pages[1]["events"][3]["id"], "3")
        self.assertEqual(pages[-1]["events"][0]["id"], "late")
        self.assertNotIn("tomorrow",
                         [e["id"] for p in pages for e in p["events"]])

        tomorrow = daily_matchup_pages(events,
                                       datetime(2026, 11, 21, 8, tzinfo=PT))
        self.assertEqual(len(tomorrow), 1)
        self.assertEqual(tomorrow[0]["events"][0]["id"], "tomorrow")

    def test_live_scores_never_appear_in_pregame_slate(self):
        games = [event("live", state="in"), event("future", minute=15)]
        pages = daily_matchup_pages(games,
                                   datetime(2026, 11, 20, 19, tzinfo=PT))
        self.assertEqual([p["kind"] for p in pages], ["game", "game"])

    def test_no_stale_final_or_fake_game(self):
        pages = daily_matchup_pages(
            [event("yesterday", day=19, state="post")],
            datetime(2026, 11, 20, 10, tzinfo=PT))
        self.assertEqual(pages, [])

    def test_overnight_live_game_remains_visible(self):
        pages = daily_matchup_pages(
            [event("late", day=19, hour=23, state="in")],
            datetime(2026, 11, 20, 0, 30, tzinfo=PT))
        self.assertEqual(pages[0]["events"][0]["id"], "late")


class RendererTests(unittest.TestCase):
    def test_all_supported_leagues_have_native_slate_and_feature(self):
        logo = dark_logo()
        games = [event(str(i), minute=i * 10) for i in range(4)]
        with tempfile.TemporaryDirectory() as tmp, patch(
                "render.matchup_slate._logo", return_value=logo):
            for league in LEAGUES:
                with self.subTest(league=league):
                    slate = render_slate(
                        games, league, 1, Path(tmp) / f"{league}_slate.png")
                    feature = render_feature(
                        games[0], league, Path(tmp) / f"{league}_feature.png")
                    self.assertEqual(slate.size, (128, 64))
                    self.assertEqual(feature.size, (128, 64))
                    self.assertNotEqual(feature.getpixel((15, 10)),
                                        feature.getpixel((115, 10)))

    def test_golf_header_pips_leave_fourth_score_row_untouched(self):
        players = [{"name": "Player " + str(i), "position": i + 1,
                    "thru": "F", "score": "-3"} for i in range(8)]
        with tempfile.TemporaryDirectory() as tmp:
            a = Path(tmp) / "a.png"
            b = Path(tmp) / "b.png"
            board = {"title": "Masters", "round": 2, "players": players}
            render_golf(board, {}, a, page=0)
            render_golf(board, {}, b, page=1)
            with Image.open(a) as first, Image.open(b) as second:
                self.assertNotEqual(first.getpixel((111, 12)),
                                    second.getpixel((111, 12)))
                self.assertEqual(first.getpixel((110, 63)),
                                 second.getpixel((110, 63)))


class WorkerTests(unittest.TestCase):
    def test_non_nfl_pages_rotate_with_global_indicator(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = Path(tmp) / "settings.json"
            config.write_text(json.dumps({"league": "nba", "power": "on",
                                          "profile": "enhanced_128x64"}))
            worker = VirtualWorker(config)
            games = [event(str(i)) for i in range(4)]
            pages = [{"kind": "slate", "events": games, "page": i,
                      "key": ("slate", ("0", "1", "2", "3"), i)}
                     for i in range(2)]
            with patch.object(worker, "fetch", return_value=games), \
                 patch.object(worker, "render",
                              return_value="enhanced_128x64") as render, \
                 patch("sportsmatrix.selection.daily_matchup_pages",
                       return_value=pages), \
                 patch("sportsmatrix.worker.STATUS", Path(tmp) / "state.json"), \
                 patch("sportsmatrix.worker.time.monotonic",
                       side_effect=[100, 113]):
                self.assertEqual(worker.tick()["event_id"], "nba-day-1-of-2")
                self.assertEqual(worker.tick()["event_id"], "nba-day-2-of-2")
                self.assertEqual(render.call_args.kwargs["carousel"], (1, 2))
                self.assertEqual(render.call_args.args[2], 1)

    def test_golf_worker_page_argument_unchanged(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = Path(tmp) / "settings.json"
            config.write_text(json.dumps({"league": "golf", "power": "on"}))
            worker = VirtualWorker(config)
            board = {"players": [{"name": "P"}] * 8}
            with patch.object(worker, "fetch", return_value=board), \
                 patch.object(worker, "render",
                              return_value="enhanced_128x64") as render, \
                 patch("sportsmatrix.worker.STATUS", Path(tmp) / "state.json"), \
                 patch("sportsmatrix.worker.time.monotonic",
                       side_effect=[100]):
                worker.tick()
                self.assertEqual(render.call_args.args[2], 1)
                self.assertIsNone(render.call_args.kwargs["carousel"])


if __name__ == "__main__":
    unittest.main()
