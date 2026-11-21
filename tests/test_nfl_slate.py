"""Regression tests for native 128x64 NFL slate pages and alpha-aware artwork."""
import json
from datetime import datetime, timedelta, timezone
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from PIL import Image, ImageDraw
from render.nfl_slate import prepare_logo, render_slate


def event(i, state="pre"):
    return {"id": str(i), "date": (datetime.now(timezone.utc) + timedelta(days=2)).isoformat(),
            "status": {"type": {"state": state}},
            "competitions": [{"competitors": [
                {"homeAway": "away", "team": {
                    "id": str(i*2), "abbreviation": "BUF", "color": "00338D"}},
                {"homeAway": "home", "team": {
                    "id": str(i*2+1), "abbreviation": "MIA", "color": "008E97"}}
            ]}]}


class SlateTests(unittest.TestCase):
    def test_alpha_trim_and_size(self):
        source = Image.new("RGBA", (80, 80), (0, 0, 0, 0))
        ImageDraw.Draw(source).ellipse((25, 15, 60, 55), fill=(255, 90, 30, 255))
        result = prepare_logo(source)
        self.assertLessEqual(result.width, 22)
        self.assertLessEqual(result.height, 17)
        self.assertEqual(result.getpixel((0, 0))[3], 0)

    def test_two_pages_are_native_and_distinct(self):
        events = [event(i) for i in range(6)]
        events[1]["competitions"][0]["competitors"][0]["team"]["color"] = "FFB612"
        events[3]["competitions"][0]["competitors"][0]["team"]["color"] = "FFB612"
        with tempfile.TemporaryDirectory() as temp, patch(
                "render.nfl_slate.team_logo", return_value=None):
            first = render_slate(events, 0, Path(temp) / "a.png")
            second = render_slate(events, 1, Path(temp) / "b.png")
            self.assertEqual(first.size, (128, 64))
            self.assertNotEqual(first.tobytes(), second.tobytes())
            self.assertNotEqual(first.getpixel((20, 10)), first.getpixel((20, 31)))

    def test_partial_page_and_empty_input(self):
        with tempfile.TemporaryDirectory() as temp, patch(
                "render.nfl_slate.team_logo", return_value=None):
            result = render_slate([event(i) for i in range(4)], 1,
                                  Path(temp) / "c.png")
            self.assertEqual(result.size, (128, 64))
        with self.assertRaises(ValueError):
            render_slate([])

    def test_worker_rotates_pregame_pages(self):
        from sportsmatrix.worker import VirtualWorker
        with tempfile.TemporaryDirectory() as temp:
            config = Path(temp) / "settings.json"
            config.write_text(json.dumps({"league": "nfl", "power": "on",
                                          "profile": "enhanced_128x64"}))
            worker = VirtualWorker(config)
            games = [event(i) for i in range(6)]
            pages = [
                {"kind": "slate", "events": games, "page": i,
                 "key": ("slate", tuple(str(g["id"]) for g in games), i)}
                for i in range(2)
            ]
            with patch.object(worker, "fetch", return_value=games), \
                 patch.object(worker, "render", return_value="enhanced_128x64"), \
                 patch("sportsmatrix.selection.nfl_weekend_pages", return_value=pages), \
                 patch("sportsmatrix.worker.STATUS", Path(temp) / "state.json"), \
                 patch("sportsmatrix.worker.time.monotonic", side_effect=[100, 113]):
                self.assertEqual(worker.tick()["event_id"], "nfl-weekend-1-of-2")
                self.assertEqual(worker.tick()["event_id"], "nfl-weekend-2-of-2")


if __name__ == "__main__":
    unittest.main()
