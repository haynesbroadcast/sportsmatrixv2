"""Regression coverage for true-black LED background pixels."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image
from render import cfb_v2, nfl_v2, nhl_v2


def scheduled_event():
    return {
        "name": "Away at Home",
        "date": "2026-11-15T20:00:00Z",
        "status": {"type": {"state": "pre"}},
        "competitions": [{
            "competitors": [
                {"homeAway": "away", "team": {"id": "1", "abbreviation": "AWY"}},
                {"homeAway": "home", "team": {"id": "2", "abbreviation": "HME"}},
            ]
        }],
    }


class TrueBlackBackgroundTests(unittest.TestCase):
    def test_football_and_hockey_frames_have_off_background_pixels(self):
        for renderer in (cfb_v2, nfl_v2, nhl_v2):
            with self.subTest(renderer=renderer.__name__):
                with tempfile.TemporaryDirectory() as directory:
                    target = Path(directory) / "render.png"
                    with (
                        patch.object(renderer, "OUTPUT", target),
                        patch.object(renderer, "logo", return_value=None),
                    ):
                        renderer.render(scheduled_event())
                    with Image.open(target) as image:
                        self.assertEqual(image.size, (128, 64))
                        self.assertEqual(image.convert("RGB").getpixel((0, 63)), (0, 0, 0))


if __name__ == "__main__":
    unittest.main()
