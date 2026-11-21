"""Regression tests for native 128x64 NFL slate pages and alpha-aware artwork."""
import json
from datetime import datetime, timedelta, timezone
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from PIL import Image, ImageDraw
from render.nfl_slate import prepare_logo, render_slate, render_feature


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

    def test_side_strip_identifies_day_not_pt(self):
        sun = event(1)
        mon = event(2)
        sun["date"] = "2026-11-22T10:00:00-08:00"
        mon["date"] = "2026-11-23T10:00:00-08:00"
        with tempfile.TemporaryDirectory() as temp, patch(
                "render.nfl_slate.team_logo", return_value=None):
            a = render_slate([sun, sun], output=Path(temp) / "sun.png")
            b = render_slate([mon, mon], output=Path(temp) / "mon.png")
            self.assertNotEqual(a.crop((0, 0, 11, 58)).tobytes(),
                                b.crop((0, 0, 11, 58)).tobytes())

    def test_late_kickoff_uses_broadcast_hour_not_minutes(self):
        one = event(1)
        two = event(2)
        one["date"] = "2026-11-22T13:05:00-08:00"
        two["date"] = "2026-11-22T13:25:00-08:00"
        with tempfile.TemporaryDirectory() as temp, patch(
                "render.nfl_slate.team_logo", return_value=None):
            a = render_slate([one, one], output=Path(temp) / "105.png")
            b = render_slate([two, two], output=Path(temp) / "125.png")
            self.assertEqual(a.crop((0, 0, 11, 58)).tobytes(),
                             b.crop((0, 0, 11, 58)).tobytes())

    def test_one_game_overflow_keeps_centered_slate_row(self):
        games = [event(i) for i in range(7)]
        with tempfile.TemporaryDirectory() as temp, patch(
                "render.nfl_slate.team_logo", return_value=None):
            frame = render_slate(games, 2, Path(temp) / "overflow.png")
            self.assertEqual(frame.size, (128, 64))
            self.assertEqual(frame.getpixel((20, 5)), (0, 0, 0))
            self.assertNotEqual(frame.getpixel((20, 30)), (0, 0, 0))

    def test_feature_header_reflects_broadcast(self):
        mon = event(1)
        sun = event(2)
        mon["date"] = "2026-11-23T17:15:00-08:00"
        sun["date"] = "2026-11-22T17:20:00-08:00"
        with tempfile.TemporaryDirectory() as temp, patch(
                "render.nfl_v2.logo", return_value=None):
            monday = render_feature(mon, Path(temp) / "monday.png")
            sunday = render_feature(sun, Path(temp) / "sunday.png")
            self.assertNotEqual(monday.crop((35, 2, 95, 12)).tobytes(),
                                sunday.crop((35, 2, 95, 12)).tobytes())

    def test_standalone_feature_is_native(self):
        sample = event(1)
        sample["date"] = "2026-11-22T17:20:00-08:00"
        logo = Image.new("RGBA", (20, 20), (255, 100, 20, 220))
        with tempfile.TemporaryDirectory() as temp, patch(
                "render.nfl_v2.logo", return_value=logo):
            result = render_feature(sample, Path(temp) / "feature.png")
            self.assertEqual(result.size, (128, 64))
            self.assertNotEqual(result.getpixel((5, 10)),
                                result.getpixel((120, 10)))

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
                self.assertEqual(worker.render.call_args.kwargs["carousel"], (1, 2))


if __name__ == "__main__":
    unittest.main()
