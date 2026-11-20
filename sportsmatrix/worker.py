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
    def render(self, league, event, page=0):
        if event is None:
            from render.other_sports import render_no_games, OUTPUT
            render_no_games(league)
        elif league == "nhl":
            from render.nhl_v2 import render, OUTPUT
            render(event)
        elif league == "nfl" and isinstance(event, list):
            from render.nfl_slate import render_slate, OUTPUT
            render_slate(event, page=page)
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
            ident=str(self.page)
        else:
            candidates=choose(self.events,prefs)
            if league == "nfl":
                from .selection import nfl_broadcast_window
                candidates=nfl_broadcast_window(candidates)
            if not candidates:return None
            # Pregame windows show three matchups per 128x64 page. Keep the
            # existing full-screen renderer for live games, finals and single
            # matchups, so scores and game situations are never hidden.
            slate = (league == "nfl" and len(candidates) > 1 and
                     all(e.get("status", {}).get("type", {}).get("state") == "pre"
                         for e in candidates))
            if slate:
                from render.nfl_slate import PER_PAGE, PAGE_SECONDS
                signature = tuple(str(e.get("id")) for e in candidates)
                pages = (len(candidates) + PER_PAGE - 1) // PER_PAGE
                if signature != self.slate_signature:
                    self.slate_signature = signature
                    self.page, self.last_rotate = 0, now
                elif now - self.last_rotate >= PAGE_SECONDS:
                    self.page = (self.page + 1) % pages
                    self.last_rotate = now
                event = candidates
                ident = f"slate-{self.page + 1}-of-{pages}"
            else:
                self.slate_signature = None
                ids=[str(e.get("id")) for e in candidates]
                if self.current_id not in ids:
                    self.current_id=ids[0];self.last_rotate=now
                current=candidates[ids.index(self.current_id)]
                if now-self.last_rotate>=duration(current,prefs):
                    self.current_id=ids[(ids.index(self.current_id)+1)%len(ids)]
                    self.last_rotate=now
                event=candidates[ids.index(self.current_id)]
                ident=self.current_id
        if settings.get("power", "on")=="off": return None
        profile=self.render(league,event,self.page)
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
