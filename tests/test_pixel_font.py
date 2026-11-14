import unittest
from unittest.mock import patch
from pathlib import Path
from tempfile import TemporaryDirectory

from PIL import Image
from render.pixel_font import GLYPHS, text_width, draw_text, center_text
from render import nfl_v2, nhl_v2


def live_game():
    return {
        "name": "Away at Home", "date": "2026-11-15T20:00:00Z",
        "status": {"type": {"state": "in"}, "period": 3, "displayClock": "05:52"},
        "competitions": [{
            "competitors": [
                {"homeAway": "away", "score": "13", "team": {"id": "1", "abbreviation": "AWY"},
                 "statistics": [{"name": "shots", "displayValue": "23"}]},
                {"homeAway": "home", "score": "10", "team": {"id": "2", "abbreviation": "HME"},
                 "statistics": [{"name": "shots", "displayValue": "18"}]},
            ],
            "situation": {"awayTimeouts": 2, "homeTimeouts": 1,
                          "shortDownDistanceText": "2nd & 8",
                          "possessionText": "AWY 38", "possession": "1"}
        }],
    }


class BitmapTests(unittest.TestCase):
    def test_all_glyphs_exactly_five_by_seven(self):
        for char, rows in GLYPHS.items():
            with self.subTest(char=char):
                self.assertEqual(len(rows), 7)
                self.assertTrue(all(len(row) == 5 and set(row) <= {"0", "1"} for row in rows))

    def test_bitmap_labels_use_only_foreground_and_black(self):
        im = Image.new("RGB", (128, 64), "black")
        center_text(im, 64, 6, "SHOTS", "#e9c56c")
        self.assertEqual(text_width("SHOTS"), 29)
        colors = set(im.getdata())
        self.assertEqual(colors, {(0, 0, 0), (233, 197, 108)})
        self.assertEqual(im.getpixel((0, 0)), (0, 0, 0))

    def test_down_distance_compression_keeps_the_distance(self):
        self.assertEqual(nfl_v2.compact_down("2nd & 8"), "2&8")
        self.assertEqual(nfl_v2.compact_down("1st & 10"), "1&10")
        self.assertEqual(nfl_v2.compact_down("3rd & Goal"), "3&G")

    def test_renderers_and_dimmed_timeout_pips(self):
        event = live_game()
        for renderer in (nfl_v2, nhl_v2):
            with self.subTest(renderer=renderer.__name__), TemporaryDirectory() as root:
                output = Path(root) / "frame.png"
                with patch.object(renderer, "OUTPUT", output), patch.object(renderer, "logo", return_value=None):
                    renderer.render(event)
                with Image.open(output) as img:
                    self.assertEqual(img.size, (128, 64))
                    self.assertEqual(img.getpixel((0, 63)), (0, 0, 0))
                    if renderer is nfl_v2:
                        self.assertEqual(img.getpixel((18, 60)), (233, 197, 108))
                        self.assertEqual(img.getpixel((32, 60)), (12, 10, 5))
                        self.assertEqual(img.getpixel((94, 60)), (233, 197, 108))
                        self.assertEqual(img.getpixel((101, 60)), (12, 10, 5))


if __name__ == "__main__":
    unittest.main()
