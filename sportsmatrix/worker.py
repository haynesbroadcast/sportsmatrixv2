"""Optional virtual display worker. Fetches games, never imports rgbmatrix."""
import json
import logging
import os
import shutil
import tempfile
import time
from pathlib import Path
from .configuration import ConfigStore
from .selection import choose, duration

BASE = Path(__file__).resolve().parent.parent
OUT = BASE / "output" / "virtual_live.png"
STATUS = BASE / "output" / "virtual_state.json"
LOG = logging.getLogger("sportsmatrix.worker")
TEAM_SLATE_LEAGUES = frozenset(("nhl", "cfb", "nba", "wnba", "mls", "nwsl", "epl"))

class VirtualWorker:
    def __init__(self, config=None):
        self.store = ConfigStore(config or os.environ.get("SPORTSMATRIX_CONFIG", BASE / "config/settings.json"))
        self.league = None
        self.events = []
        self.current_id = None
        self.last_fetch = 0
        self.last_rotate = 0
        self.page = 0
        self.last_render = None
        self.slate_signature = None
        self.other_signature = None
        self.other_page_key = None
    def fetch(self, league):
        if league == "nhl":
            from nhl_runtime import fetch_events
            return fetch_events()
        if league == "nfl":
            from nfl_runtime import fetch_events
            return fetch_events()
        if league == "cfb":
            from cfb_runtime import fetch_events
            return fetch_events()
        if league == "golf":
            from plugins.espn import fetch_golf_leaderboard
            return fetch_golf_leaderboard()
        from .other_feeds import fetch_events
        return fetch_events(league)
    def render(self, league, event, page=0, carousel=None):
        if event is None:
            from render.other_sports import render_no_games, OUTPUT
            render_no_games(league)
        elif league in TEAM_SLATE_LEAGUES and isinstance(event, list):
            from render.matchup_slate import render_slate
            OUTPUT = BASE / "output" / f"{league}_slate.png"
            render_slate(event, league, page=page, output_path=OUTPUT)
        elif league in TEAM_SLATE_LEAGUES and event.get(
                "status", {}).get("type", {}).get("state") == "pre":
            from render.matchup_slate import render_feature
            OUTPUT = BASE / "output" / f"{league}_feature.png"
            render_feature(event, league, output_path=OUTPUT)
        elif league == "nhl":
            from render.nhl_v2 import render, OUTPUT
            render(event)
        elif league == "nfl" and isinstance(event, list):
            from render.nfl_slate import render_slate, OUTPUT
            render_slate(event, page=page)
        elif league == "nfl" and event.get("status", {}).get("type", {}).get("state") == "pre":
            from render.nfl_slate import render_feature, FEATURE_OUTPUT
            render_feature(event)
            OUTPUT = FEATURE_OUTPUT
        elif league == "nfl":
            from render.nfl_v2 import render, OUTPUT
            render(event)
        elif league == "cfb":
            from render.cfb_v2 import render, OUTPUT
            render(event)
        elif league == "golf":
            from render.golf import render_golf
            OUTPUT = BASE / "output" / "golf_v2.png"
            render_golf(event, {}, OUTPUT, page=page)
        else:
            from render.other_sports import render, OUTPUT
            render(event, league)
        from .preview import output_for
        profile = self.store.read().get("profile", "enhanced_128x64")
        image = output_for(profile, OUTPUT)
        if league in TEAM_SLATE_LEAGUES | {"nfl"} and carousel is not None:
            from render.page_indicator import draw_page_indicator
            draw_page_indicator(image, carousel[0], carousel[1])
        OUT.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=OUT.parent, suffix=".png", delete=False) as f:
            temp = Path(f.name)
        try:
            image.save(temp, format="PNG")
            os.replace(temp, OUT)
        finally:
            temp.unlink(missing_ok=True)
        return profile
    def tick(self):
        now = time.monotonic()
        settings = self.store.read()
        league = settings.get("league", "nhl")
        prefs = settings.get("sport_preferences", {}).get(league, {})
        if league != self.league:
            self.league, self.events, self.current_id, self.last_fetch, self.last_rotate = league, [], None, 0, 0
            self.page, self.slate_signature = 0, None
            self.nfl_page_key = None
            self.other_signature, self.other_page_key = None, None
        # Re-fetch all games every five minutes; update at 15 seconds while live.
        live = league == "golf" or (isinstance(self.events, list) and any(e.get("status",{}).get("type",{}).get("state")=="in" for e in self.events))
        interval = 15 if live else 300
        if self.last_fetch == 0 or now-self.last_fetch >= interval:
            try:
                fetched = self.fetch(league)
                if fetched or league not in ("nhl", "nfl", "cfb", "golf"):
                    self.events = fetched
            except Exception:
                LOG.exception("Provider fetch failed; retaining last data")
            self.last_fetch = now
        if not self.events:
            if league in ("nhl", "nfl", "cfb", "golf") or settings.get("power", "on") == "off":
                return None
            # Do not leave the last sport's pixels on screen during an off-season.
            profile = self.render(league, None)
            payload = {"league": league, "event_id": "no_games",
                       "profile": profile, "updated_at": time.time(),
                       "mode": "live_virtual"}
            STATUS.parent.mkdir(parents=True, exist_ok=True)
            temp = STATUS.with_suffix(".tmp")
            temp.write_text(json.dumps(payload))
            os.replace(temp, STATUS)
            return payload
        if league == "golf":
            board = self.events
            pages=max(1,min(4,(len(board.get("players",[]))+3)//4))
            if now-self.last_rotate>=30:
                self.page=(self.page+1)%pages
                self.last_rotate=now
            event=board
            render_page=self.page
            ident=str(self.page)
        else:
            candidates=choose(self.events,prefs)
            if league == "cfb":
                from .selection import ranked_cfb_games
                candidates = ranked_cfb_games(candidates)
            if league == "nfl":
                from .selection import nfl_weekend_pages
                from render.nfl_slate import PAGE_SECONDS
                pages = nfl_weekend_pages(candidates)
                if not pages:
                    return None
                signature = tuple(item["key"] for item in pages)
                if signature != self.slate_signature:
                    # Preserve the current page if a background ESPN refresh
                    # changes unrelated game details without changing the
                    # actual carousel order.
                    old_key = getattr(self, "nfl_page_key", None)
                    self.page = next(
                        (i for i, item in enumerate(pages) if item["key"] == old_key),
                        0)
                    self.slate_signature = signature
                    self.last_rotate = now
                current = pages[self.page]
                seconds = (PAGE_SECONDS if current["kind"] == "slate"
                           else duration(current["events"][0], prefs))
                if now - self.last_rotate >= seconds:
                    self.page = (self.page + 1) % len(pages)
                    self.last_rotate = now
                    current = pages[self.page]
                self.nfl_page_key = current["key"]
                if current["kind"] == "slate":
                    event = current["events"]
                    render_page = current["page"]
                else:
                    event = current["events"][0]
                    render_page = 0
                ident = f"nfl-weekend-{self.page + 1}-of-{len(pages)}"
            elif league in TEAM_SLATE_LEAGUES:
                from .selection import daily_matchup_pages
                from render.matchup_slate import PAGE_SECONDS
                pages = daily_matchup_pages(candidates)
                if not pages:
                    return None
                signature = tuple(item["key"] for item in pages)
                if signature != self.other_signature:
                    old_key = self.other_page_key
                    self.page = next(
                        (i for i, item in enumerate(pages) if item["key"] == old_key),
                        0)
                    self.other_signature = signature
                    self.last_rotate = now
                current = pages[self.page]
                seconds = (PAGE_SECONDS if current["kind"] == "slate"
                           else duration(current["events"][0], prefs))
                if now - self.last_rotate >= seconds:
                    self.page = (self.page + 1) % len(pages)
                    self.last_rotate = now
                    current = pages[self.page]
                self.other_page_key = current["key"]
                if current["kind"] == "slate":
                    event = current["events"]
                    render_page = current["page"]
                else:
                    event = current["events"][0]
                    render_page = 0
                ident = f"{league}-day-{self.page + 1}-of-{len(pages)}"
            else:
                ids=[str(e.get("id")) for e in candidates]
                if not ids:return None
                if self.current_id not in ids:
                    self.current_id=ids[0];self.last_rotate=now
                current=candidates[ids.index(self.current_id)]
                if now-self.last_rotate>=duration(current,prefs):
                    self.current_id=ids[(ids.index(self.current_id)+1)%len(ids)]
                    self.last_rotate=now
                event=candidates[ids.index(self.current_id)]
                ident=self.current_id
            if league not in TEAM_SLATE_LEAGUES | {"nfl"}:
                render_page = self.page
        if settings.get("power", "on")=="off": return None
        profile=self.render(
            league, event, render_page,
            carousel=(self.page, len(pages))
            if league in TEAM_SLATE_LEAGUES | {"nfl"} else None)
        payload={"league":league,"event_id":ident,"profile":profile,"updated_at":time.time(),"mode":"live_virtual"}
        STATUS.parent.mkdir(parents=True, exist_ok=True)
        temp=STATUS.with_suffix(".tmp")
        temp.write_text(json.dumps(payload))
        os.replace(temp,STATUS)
        return payload

def main():
    logging.basicConfig(level=logging.INFO)
    worker=VirtualWorker()
    while True:
        try:
            result=worker.tick()
            if result: LOG.info("Virtual: %s %s",result["league"],result["event_id"])
        except Exception: LOG.exception("Worker tick failed")
        time.sleep(5)

if __name__=="__main__": main()
