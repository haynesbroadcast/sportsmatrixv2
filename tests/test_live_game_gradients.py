"""Live/final gradient continuity with approved pregame team-color theme."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image, ImageDraw

from render.game_background import game_background
from render import nfl_v2, cfb_v2, nhl_v2, other_sports


def event(state="in"):
    return {
        "id": "sample",
        "name": "Away at Home",
        "date": "2026-11-22T01:00:00Z",
        "status": {
            "type": {"state": state, "shortDetail": "Final"},
            "period": 3, "displayClock": "05:42",
        },
        "competitions": [{
            "situation": {
                "possession": "1",
                "shortDownDistanceText": "2nd & 8",
                "awayTimeouts": 2, "homeTimeouts": 1,
                "powerPlay": True,
            },
            "competitors": [
                {"homeAway": "away", "score": "21",
                 "curatedRank": {"current": 9},
                 "team": {"id": "1", "abbreviation": "AWY",
                          "color": "00338D"}},
                {"homeAway": "home", "score": "17",
                 "team": {"id": "2", "abbreviation": "HME",
                          "color": "E31837"}},
            ],
        }],
    }


def logo():
    icon = Image.new("RGBA", (20, 20))
    ImageDraw.Draw(icon).ellipse((1, 1, 18, 18),
                                 fill=(10, 24, 64, 255))
    return icon


class GradientTests(unittest.TestCase):
    def test_gradient_uses_both_team_colors_and_has_dark_center(self):
        away = {"color": "00338D"}
        home = {"color": "E31837"}
        image = game_background(away, home)
        self.assertEqual(image.size, (128, 64))
        left = image.getpixel((5, 18))
        right = image.getpixel((123, 18))
        self.assertGreater(left[2], left[0])
        self.assertGreater(right[0], right[2])
        center = image.getpixel((64, 18))
        self.assertLess(sum(center), (sum(left) + sum(right)) / 2)
        self.assertNotEqual(image.getpixel((5, 18)),
                            image.getpixel((5, 50)))

    def test_final_quieter_than_live(self):
        away = {"color": "FFFFFF"}
        home = {"color": "FFFFFF"}
        live = game_background(away, home, "in")
        final = game_background(away, home, "post")
        self.assertLess(sum(final.getpixel((20, 20))),
                        sum(live.getpixel((20, 20))))
        self.assertLess(max(live.getpixel((64, 45))), 100)

    def test_invalid_team_colors_fall_back_safely(self):
        image = game_background({"color": "not-hex"}, {})
        self.assertNotEqual(image.getpixel((0, 0)), (0, 0, 0))
        with self.assertRaises(ValueError):
            game_background({}, {}, "pre")


class LiveRendererTests(unittest.TestCase):
    def test_nfl_cfb_nhl_live_and_final_keep_score_first(self):
        modules = (nfl_v2, cfb_v2, nhl_v2)
        with tempfile.TemporaryDirectory() as temp:
            for module in modules:
                for state in ("in", "post"):
                    with self.subTest(module=module.__name__, state=state):
                        destination = Path(temp) / (
                            module.__name__.split(".")[-1] + state + ".png")
                        with patch.object(module, "OUTPUT", destination), \
                             patch.object(module, "logo", return_value=logo()):
                            module.render(event(state))
                        with Image.open(destination) as frame:
                            self.assertEqual(frame.size, (128, 64))
                            self.assertNotEqual(frame.getpixel((6, 12)),
                                                (0, 0, 0))
                            self.assertNotEqual(frame.getpixel((120, 12)),
                                                (0, 0, 0))
                            self.assertGreater(max(frame.getpixel((26, 49))),
                                               25)

    def test_other_team_sports_share_live_theme(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(
                other_sports, "logo", return_value=logo()):
            for league in ("nba", "wnba", "mls", "nwsl", "epl"):
                for state in ("in", "post"):
                    with self.subTest(league=league, state=state):
                        destination = Path(temp) / f"{league}-{state}.png"
                        other_sports.render(event(state), league, destination)
                        with Image.open(destination) as frame:
                            self.assertNotEqual(frame.getpixel((6, 12)),
                                                (0, 0, 0))
                            self.assertNotEqual(frame.getpixel((120, 12)),
                                                (0, 0, 0))

    def test_pregame_full_game_renderer_stays_black(self):
        with tempfile.TemporaryDirectory() as temp:
            destination = Path(temp) / "pregame.png"
            with patch.object(nfl_v2, "OUTPUT", destination), \
                 patch.object(nfl_v2, "logo", return_value=None):
                nfl_v2.render(event("pre"))
            with Image.open(destination) as frame:
                self.assertEqual(frame.getpixel((0, 0)), (0, 0, 0))

    def test_mlb_score_first_layout_is_not_replaced(self):
        with patch("render.mlb_board.render_mlb",
                   return_value=Path("/tmp/score.png")) as renderer, \
             patch.object(other_sports, "game_background") as gradient:
            other_sports.render(event("in"), "mlb")
            renderer.assert_called_once()
            gradient.assert_not_called()


if __name__ == "__main__":
    unittest.main()
