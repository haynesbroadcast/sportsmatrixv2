import io
import unittest
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch, MagicMock
from zoneinfo import ZoneInfo

from PIL import Image
from render.other_sports import render, render_no_games, SPORT
from sportsmatrix.other_feeds import ESPN_PATHS, fetch_events, parse_pwhl, prioritize
from sportsmatrix.registry import supported
from sportsmatrix.preview import render_fixture
from sportsmatrix.worker import VirtualWorker


def event(score_away="108", score_home="112", state="in"):
    return {
        "id": "test1", "date": "2026-11-15T20:00:00Z",
        "status": {"type": {"state": state, "shortDetail": "LIVE"},
                   "period": 3, "displayClock": "05:42"},
        "competitions": [{
            "competitors": [
                {"homeAway": "away", "score": score_away,
                 "team": {"id": "1", "abbreviation": "AWY"}},
                {"homeAway": "home", "score": score_home,
                 "team": {"id": "2", "abbreviation": "HME"}},
            ],
            "situation": {"outs": 2, "onFirst": True, "onSecond": False,
                          "onThird": True, "isBottomInning": True},
        }],
    }


class OtherSportsTests(unittest.TestCase):
    def test_all_remaining_leagues_enabled(self):
        self.assertEqual(set(SPORT), {"nba", "wnba", "mlb", "mls", "nwsl", "epl", "pwhl", "pll"})
        self.assertTrue(set(SPORT).issubset(supported()))

    def test_all_new_leagues_render_and_preview(self):
        with patch("render.other_sports.logo", return_value=None):
            for league in SPORT:
                with self.subTest(league=league), TemporaryDirectory() as directory:
                    path = Path(directory) / "test.png"
                    render(event(), league, path)
                    with Image.open(path) as im:
                        self.assertEqual(im.size, (128, 64))
                        self.assertEqual(im.getpixel((0, 0)), (0, 0, 0))
                        self.assertGreater(len(im.getcolors(128 * 64)), 1)
                    for profile, shape in (("enhanced_128x64", (128, 64)), ("compact_64x32", (64, 32))):
                        data = render_fixture(league, profile)
                        self.assertEqual(Image.open(io.BytesIO(data)).size, shape)

    def test_basketball_three_digits_fit_and_no_fake_pregame_score(self):
        with patch("render.other_sports.logo", return_value=None), TemporaryDirectory() as directory:
            path = Path(directory) / "test.png"
            render(event("128", "143"), "nba", path)
            with Image.open(path) as im:
                self.assertEqual(im.size, (128, 64))
                self.assertTrue(any(im.getpixel((x, y)) != (0, 0, 0)
                                    for x in range(4, 49) for y in range(36, 63)))
            render(event(state="pre"), "nba", path)
            with Image.open(path) as im:
                # Scores are replaced with abbreviations before tipoff.
                self.assertEqual(im.getpixel((26, 61)), (0, 0, 0))

    def test_no_games_screen_and_worker_publish(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "no_games.png"
            render_no_games("wnba", path)
            with Image.open(path) as image:
                self.assertEqual(image.size, (128, 64))
                self.assertGreater(len(image.getcolors(128 * 64)), 1)
            worker = VirtualWorker(root / "settings.json")
            with patch("sportsmatrix.other_feeds.fetch_events", return_value=[]), \
                 patch("sportsmatrix.worker.OUT", root / "live.png"), \
                 patch("sportsmatrix.worker.STATUS", root / "state.json"):
                worker.store.update({"league": "wnba"})
                # Override renderer output to avoid writing to the repository
                # while still exercising the real no-games frame.
                from render import other_sports
                with patch.object(other_sports, "OUTPUT", root / "render.png"):
                    result = worker.tick()
                    self.assertEqual(result["event_id"], "no_games")
                    self.assertTrue((root / "live.png").exists())

    def test_espn_feed_mapping_and_worker_dispatch(self):
        self.assertEqual(len(ESPN_PATHS), 7)
        response = MagicMock()
        response.json.return_value = {"events": [event()]}
        with patch("sportsmatrix.other_feeds.requests.get", return_value=response) as get:
            result = fetch_events("nba")
            self.assertEqual(len(result), 1)
            self.assertIn("basketball/nba/scoreboard", get.call_args.args[0])
            self.assertIn("dates", get.call_args.kwargs["params"])
        with TemporaryDirectory() as directory:
            worker = VirtualWorker(Path(directory) / "settings.json")
            with patch("sportsmatrix.other_feeds.fetch_events", return_value=[event()]) as fetch:
                self.assertEqual(len(worker.fetch("mlb")), 1)
                fetch.assert_called_once_with("mlb")

    def test_pwhl_adapter_no_invented_scores(self):
        payload = {"SiteKit": {"Scorebar": [
            {"ID": "44", "Date": "2026-11-15", "ScheduledTime": "15:00",
             "GameStatus": "1", "home_team_name": "Toronto",
             "visiting_team_name": "Montreal"},
        ]}}
        games = parse_pwhl(payload)
        self.assertEqual(len(games), 1)
        self.assertEqual(games[0]["id"], "pwhl_44")
        self.assertEqual(games[0]["status"]["type"]["state"], "pre")
        self.assertIsNone(games[0]["competitions"][0]["competitors"][0]["score"])

    def test_prioritize_live_before_upcoming(self):
        now = datetime(2026, 11, 15, 11, tzinfo=ZoneInfo("America/Los_Angeles"))
        game_a = event(state="pre")
        game_b = event(state="in")
        self.assertEqual(prioritize([game_a, game_b], now)[0]["status"]["type"]["state"], "in")


if __name__ == "__main__":
    unittest.main()
