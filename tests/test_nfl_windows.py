from datetime import datetime, timedelta, timezone
from sportsmatrix.selection import nfl_broadcast_window


NOW = datetime(2026, 11, 15, 21, 0, tzinfo=timezone.utc)


def game(ident, minutes, state):
    return {"id": ident, "date": (NOW + timedelta(minutes=minutes)).isoformat(),
            "status": {"type": {"state": state}}}


def test_live_games_hide_future_windows():
    games = [game("live", -40, "in"), game("tonight", 400, "pre"),
             game("next-week", 10080, "pre")]
    assert [e["id"] for e in nfl_broadcast_window(games, NOW)] == ["live"]


def test_next_kickoff_group_only():
    games = [game("early1", 30, "pre"), game("early2", 45, "pre"),
             game("late", 210, "pre"), game("next-week", 10080, "pre")]
    assert [e["id"] for e in nfl_broadcast_window(games, NOW)] == ["early1", "early2"]


def test_sunday_finals_beat_next_week():
    games = [game("finished", -120, "post"), game("next-week", 10080, "pre")]
    assert [e["id"] for e in nfl_broadcast_window(games, NOW)] == ["finished"]
