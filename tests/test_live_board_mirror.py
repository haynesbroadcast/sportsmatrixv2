"""The On the Board panel must never display a stale or recorded fixture."""
import io
import json
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image

from sportsmatrix.server import create_app


class LiveBoardMirrorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.out = self.root / "output"
        self.out.mkdir()
        self.base_patch = patch("sportsmatrix.server.BASE", self.root)
        self.base_patch.start()
        self.addCleanup(self.base_patch.stop)
        self.client = create_app(self.root / "settings.json").test_client()

    def write_frame(self, league="nhl", profile="enhanced_128x64",
                    worker_age=1, hardware_age=1, frame_active=True):
        Image.new("RGB", (128, 64), (31, 64, 128)).save(
            self.out / "virtual_live.png")
        (self.out / "virtual_state.json").write_text(json.dumps({
            "league": league, "profile": profile,
            "updated_at": time.time() - worker_age}))
        (self.out / "hardware_state.json").write_text(json.dumps({
            "updated_at": time.time() - hardware_age,
            "frame_active": frame_active}))

    def test_missing_live_frame_returns_no_sample(self):
        response = self.client.get("/api/v1/board.png")
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json["ok"], False)
        self.assertFalse(self.client.get("/api/v1/status").json["board_active"])

    def test_exact_active_frame_is_served_without_cache(self):
        self.write_frame()
        status = self.client.get("/api/v1/status").json
        self.assertTrue(status["board_active"])
        self.assertEqual(status["board_league"], "nhl")
        self.assertEqual(status["version"], "0.22")
        response = self.client.get("/api/v1/board.png")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, "image/png")
        self.assertIn("no-store", response.headers["Cache-Control"])
        with Image.open(io.BytesIO(response.data)) as image:
            self.assertEqual(image.size, (128, 64))
            self.assertEqual(image.getpixel((0, 0)), (31, 64, 128))

    def test_mismatched_selected_league_is_never_mirrored(self):
        self.write_frame(league="cfb")
        self.assertFalse(self.client.get("/api/v1/status").json["board_active"])
        self.assertEqual(self.client.get("/api/v1/board.png").status_code, 503)

    def test_stale_worker_or_hardware_is_not_mirrored(self):
        for worker_age, hardware_age in ((125, 1), (1, 20)):
            with self.subTest(worker_age=worker_age, hardware_age=hardware_age):
                self.write_frame(worker_age=worker_age,
                                 hardware_age=hardware_age)
                self.assertFalse(
                    self.client.get("/api/v1/status").json["board_active"])
                self.assertEqual(
                    self.client.get("/api/v1/board.png").status_code, 503)

    def test_hardware_blank_or_power_off_is_not_mirrored(self):
        self.write_frame(frame_active=False)
        self.assertFalse(self.client.get("/api/v1/status").json["board_active"])
        self.write_frame()
        self.assertEqual(self.client.put(
            "/api/v1/settings", json={"power": "off"}).status_code, 200)
        self.assertEqual(self.client.get("/api/v1/board.png").status_code, 503)

    def test_ui_never_uses_fixture_endpoint_for_on_board(self):
        html = self.client.get("/").get_data(as_text=True)
        self.assertIn("Exact current worker frame", html)
        self.assertIn("setInterval(refreshBoard, 5000)", html)
        self.assertIn("'/api/v1/board.png?t='", html)
        self.assertNotIn("'/api/v1/preview.png?league='", html)
        self.assertIn("No active scoreboard frame", html)


if __name__ == "__main__":
    unittest.main()
