import io
import json
import sys
import urllib.request
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
from PIL import Image, ImageDraw, ImageFont
from .pixel_font import center_text as bitmap_center
from .timeout_pips import draw_timeouts
from .nfl_v2 import compact_down

BASE = Path(__file__).resolve().parent.parent
CACHE = BASE / "assets/cfb"
OUTPUT = BASE / "output/cfb_v2.png"
API = ("https://site.api.espn.com/apis/site/v2/"
       "sports/football/college-football/scoreboard"
       "?groups=80&limit=200")
TZ = ZoneInfo("America/Los_Angeles")
GOLD, WHITE, DIM = "#e9c56c", "#f5f6f8", "#344253"

def fetch(url):
    req = urllib.request.Request(
        url, headers={"User-Agent": "SportsMatrixV2/1.0"})
    with urllib.request.urlopen(req, timeout=15) as r:
        return r.read()

def font(size):
    return ImageFont.truetype(
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf", size)

def center(d, x, y, text, size, color=WHITE):
    f = font(size)
    box = d.textbbox((0, 0), str(text), font=f)
    d.text((int(x-(box[2]-box[0])/2), y), str(text),
           font=f, fill=color)

def rank(c):
    try:
        n = int(c.get("curatedRank", {}).get("current", 99))
        return n if 1 <= n <= 25 else None
    except (TypeError, ValueError):
        return None

def logo(team):
    team_id = str(team.get("id", ""))
    if not team_id:
        return None
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / (team_id + ".png")
    if not path.exists():
        logos = team.get("logos") or []
        url = team.get("logo") or (
            logos[0].get("href") if logos else None
        )
        if not url:
            return None
        try:
            raw = fetch(url)
            image = Image.open(io.BytesIO(raw)).convert("RGBA")
            image.save(path)
        except Exception as e:
            print("Logo unavailable:", team_id, e)
            return None
    try:
        image = Image.open(path).convert("RGBA")
        image.thumbnail((38, 32), Image.Resampling.LANCZOS)
        return image
    except Exception:
        return None

def priority(event):
    c = event["competitions"][0]
    ranks = [rank(t) for t in c.get("competitors", [])]
    count = sum(r is not None for r in ranks)
    state = event["status"]["type"]["state"]
    category = (
        0 if state == "in" and count == 2 else
        1 if state == "in" and count else
        2 if state == "in" else
        3 if count == 2 else
        4 if count else 5
    )
    return (category, min((r for r in ranks if r), default=99),
            event.get("date", ""))

def render(event):
    comp = event["competitions"][0]
    teams = comp["competitors"]
    away = next(t for t in teams if t["homeAway"] == "away")
    home = next(t for t in teams if t["homeAway"] == "home")
    status = event["status"]
    state = status["type"]["state"]
    situation = comp.get("situation") or {}

    img = Image.new("RGB", (128, 64), "#000000")
    d = ImageDraw.Draw(img)
    # HUB75 panel: keep text glyph edges pixel-sharp, not grayscale-antialiased.
    d.fontmode = "1"
    possession = str(situation.get("possession", ""))

    for c, x in ((away, 26), (home, 102)):
        team = c["team"]
        r = rank(c)
        if r:
            bitmap_center(img, x, 0, f"#{r}", GOLD)

        icon = logo(team)
        if icon:
            img.paste(icon, (x-icon.width//2, 8), icon)
        else:
            center(d, x, 17, team.get("abbreviation", "???")[:4], 10)

        if state == "in" and possession == str(team.get("id", "")):
            d.polygon([(x+20, 25), (x+23, 28), (x+20, 31)],
                      fill=GOLD)

        if state in ("in", "post"):
            center(d, x, 35, str(c.get("score", "0")), 28)
        else:
            center(d, x, 41, team.get("abbreviation", "???")[:5], 13)

        if state == "in":
            key = ("awayTimeouts" if c["homeAway"] == "away"
                   else "homeTimeouts")
            remaining = situation.get(key)
            if remaining is not None:
                draw_timeouts(d, c["homeAway"], remaining,
                              c.get("score", "0"), GOLD)

    if state == "in":
        period = status.get("period", 0)
        clock = status.get("displayClock", "")
        period_text = (f"Q{period}" if period <= 4
                       else f"OT{period-4}")
        bitmap_center(img, 64, 1, period_text, GOLD)
        center(d, 64, 12, clock[:7], 12)

        down = situation.get("shortDownDistanceText")
        if not down and situation.get("down"):
            down = f"{situation['down']} & {situation.get('distance', '?')}"
        if down:
            bitmap_center(img, 64, 37, compact_down(down), WHITE)

        field = situation.get("possessionText")
        if field:
            center(d, 64, 51, str(field)[:8], 9, GOLD)

    elif state == "post":
        bitmap_center(img, 64, 26, "FINAL", GOLD)
    else:
        kickoff = datetime.fromisoformat(
            event["date"].replace("Z", "+00:00")).astimezone(TZ)
        bitmap_center(img, 64, 12, kickoff.strftime("%a").upper(), GOLD)
        center(d, 64, 28,
               kickoff.strftime("%I:%M%p").lstrip("0"), 9)

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    img.save(OUTPUT)
    print("Game:", event["name"])
    print("Status:", status["type"].get("shortDetail", ""))
    print("Possession:", possession or "Unavailable")
    print("Down:", situation.get("shortDownDistanceText"))
    print("Field:", situation.get("possessionText"))
    print("Preview:", OUTPUT)

def main():
    data = json.loads(fetch(API))
    events = data.get("events", [])
    if not events:
        sys.exit("ESPN returned no games.")
    render(sorted(events, key=priority)[0])

if __name__ == "__main__":
    main()
