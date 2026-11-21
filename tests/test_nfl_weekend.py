"""NFL viewing-week carousel: Thanksgiving, single games, slate overflow."""
import unittest
from datetime import datetime
from zoneinfo import ZoneInfo

from sportsmatrix.selection import nfl_weekend_pages

PT = ZoneInfo("America/Los_Angeles")


def game(name, day, hour, minute=0, state="pre"):
    start = datetime(2026, 11, day, hour, minute, tzinfo=PT)
    return {"id": name, "date": start.isoformat(),
            "status": {"type": {"state": state}}}


class WeekendCarouselTests(unittest.TestCase):
    def setUp(self):
        self.events = [
            game("tnf", 26, 17, 20),
            game("thanksgiving-early", 26, 9, 30),
            game("thanksgiving-middle", 26, 13, 30),
            game("friday", 27, 12, 0),
            *[game(f"sun-am-{i}", 29, 10, 0) for i in range(7)],
            *[game(f"sun-pm-{i}", 29, 13, 25) for i in range(4)],
            game("snf", 29, 17, 20),
            game("mnf", 30, 17, 15),
            game("next-thu", 26, 10),  # duplicate ID deliberately avoided below
        ]
        self.events.pop()  # next week's date is in December; tested separately.

    def test_wednesday_has_all_remaining_windows(self):
        now = datetime(2026, 11, 25, 12, 0, tzinfo=PT)
        pages = nfl_weekend_pages(self.events, now)
        keys = [p["events"][0]["id"] for p in pages]
        self.assertEqual(keys[:4], ["thanksgiving-early",
                                    "thanksgiving-middle", "tnf", "friday"])
        self.assertEqual(keys[-2:], ["snf", "mnf"])
        self.assertEqual(len(pages), 11)
        self.assertEqual([p["kind"] for p in pages[:4]], ["game"] * 4)
        self.assertEqual([p["kind"] for p in pages[4:7]],
                         ["slate", "slate", "game"])
        self.assertEqual([p["kind"] for p in pages[7:9]],
                         ["slate", "game"])

    def test_friday_excludes_thursday_but_keeps_sunday_and_monday(self):
        now = datetime(2026, 11, 27, 8, 0, tzinfo=PT)
        pages = nfl_weekend_pages(self.events, now)
        ids = [e["id"] for p in pages for e in p["events"]]
        self.assertNotIn("tnf", ids)
        self.assertNotIn("thanksgiving-early", ids)
        self.assertIn("friday", ids)
        self.assertIn("snf", ids)
        self.assertIn("mnf", ids)

    def test_sunday_excludes_friday_and_keeps_both_slates(self):
        now = datetime(2026, 11, 29, 9, 0, tzinfo=PT)
        pages = nfl_weekend_pages(self.events, now)
        self.assertEqual(pages[0]["kind"], "slate")
        self.assertEqual(pages[0]["page"], 0)
        self.assertEqual(pages[1]["page"], 1)
        self.assertEqual(pages[2]["kind"], "game")  # seventh early game
        self.assertEqual(pages[-1]["events"][0]["id"], "mnf")

    def test_monday_only_monday(self):
        now = datetime(2026, 11, 30, 9, 0, tzinfo=PT)
        pages = nfl_weekend_pages(self.events, now)
        self.assertEqual(len(pages), 1)
        self.assertEqual(pages[0]["events"][0]["id"], "mnf")

    def test_live_games_get_full_screen_and_future_remains(self):
        events = [game("live", 29, 10, state="in"),
                  game("pre", 29, 10), game("snf", 29, 17, 20)]
        now = datetime(2026, 11, 29, 10, 20, tzinfo=PT)
        pages = nfl_weekend_pages(events, now)
        self.assertEqual(len(pages), 3)
        self.assertTrue(all(p["kind"] == "game" for p in pages))

    def test_next_week_is_excluded(self):
        now = datetime(2026, 11, 25, 9, tzinfo=PT)
        events = [game("this-mnf", 30, 17),
                  {"id": "next-thu", "date": "2026-12-03T17:20:00-08:00",
                   "status": {"type": {"state": "pre"}}}]
        pages = nfl_weekend_pages(events, now)
        self.assertEqual([p["events"][0]["id"] for p in pages], ["this-mnf"])


if __name__ == "__main__":
    unittest.main()
