import time
from plugins.espn import fetch_golf_leaderboard

class GolfRotation:
    def __init__(self):
        self.board = None
        self.page = 0
        self.last_fetch = 0
        self.last_rotate = time.monotonic()

    def tick(self):
        now = time.monotonic()

        interval = 15 if self.board and self.board.get("live") else 300

        if self.board is None or now - self.last_fetch >= interval:
            try:
                fresh = fetch_golf_leaderboard()
                self.board = fresh
                self.last_fetch = now
            except Exception as exc:
                print("Golf ESPN fetch failed:", exc)
                self.last_fetch = now

        if self.board is None:
            return None, 0

        pages = max(
            1,
            min(4, (len(self.board.get("players", [])) + 3) // 4)
        )

        if now - self.last_rotate >= 30:
            self.page = (self.page + 1) % pages
            self.last_rotate = now

        self.page %= pages
        return self.board, self.page
