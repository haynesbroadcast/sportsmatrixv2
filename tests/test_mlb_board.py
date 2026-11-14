import io
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from PIL import Image
from render.mlb_board import draw_board, _abbr, _rhe
from sportsmatrix.preview import render_fixture


def matchup():
    return {
        "date": "2026-11-15T20:00:00Z",
        "status": {"type": {"state": "in", "shortDetail": "Top 7th"}, "period": 7},
        "competitions": [{"competitors": [
            {"homeAway": "away", "score": "7",
             "team": {"abbreviation": "LAD"},
             "statistics": [{"name": "hits", "displayValue": "10"},
                            {"name": "errors", "displayValue": "0"}]},
            {"homeAway": "home", "score": "8",
             "team": {"abbreviation": "SFG", "color": "FD5A1E"},
             "statistics": [{"name": "hits", "displayValue": "12"},
                            {"name": "errors", "displayValue": "1"}]},
        ], "situation": {"balls": 2, "strikes": 1, "outs": 2, "onFirst": True,
                          "onSecond": False, "onThird": True,
                          "isBottomInning": False}}]
    }


class MLBBoardTests(unittest.TestCase):
    def test_canonical_giants_abbreviation_and_team_totals(self):
        e = matchup()
        away, home = e["competitions"][0]["competitors"]
        self.assertEqual(_abbr(home), "SF")
        self.assertEqual(_abbr(away), "LAD")
        self.assertEqual(_rhe(away, "in"), ("7", "10", "0"))
        self.assertEqual(_rhe(home, "in"), ("8", "12", "1"))
        self.assertEqual(_rhe(home, "pre"), ("-", "-", "-"))

    def test_exact_frame_and_all_rows(self):
        image = draw_board(matchup())
        self.assertEqual(image.size, (128, 64))
        # Top state, R/H/E header, and both team rows use the full height.
        for y in (0, 5, 19, 20, 27, 28, 45, 46, 63):
            self.assertTrue(any(image.getpixel((x, y)) != (0, 0, 0)
                                for x in range(128)), y)
        # The two 4px team challenge indicators are visible in each row.
        for y in (35, 53):
            for x in (50, 60):
                self.assertNotEqual(image.getpixel((x, y)), (0, 0, 0))

    def test_sample_preview_uses_sf_lead(self):
        data = render_fixture("mlb", "enhanced_128x64")
        image = Image.open(io.BytesIO(data))
        self.assertEqual(image.size, (128, 64))
        # Source fixture uses 7–8, not the old generic 3–2 mock game.
        self.assertEqual(matchup()["competitions"][0]["competitors"][1]["score"], "8")


if __name__ == "__main__":
    unittest.main()
