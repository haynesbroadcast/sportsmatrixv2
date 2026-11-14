
import io
import json
import urllib.request
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
from PIL import Image, ImageDraw, ImageFont

BASE = Path(__file__).resolve().parent.parent
CACHE = BASE / "assets/nhl"
OUTPUT = BASE / "output/nhl_v2.png"
API = "https://site.api.espn.com/apis/site/v2/sports/hockey/nhl/scoreboard?limit=100"
TZ = ZoneInfo("America/Los_Angeles")
GOLD = "#e9c56c"
WHITE = "#f5f6f8"
DIM = "#344253"
BG = "#000000"

def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "SportsMatrixV2/1.0"})
    with urllib.request.urlopen(req, timeout=15) as response:
        return response.read()

def font(size):
    return ImageFont.truetype(
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", size
    )

def center(d, x, y, value, size, color=WHITE):
    f = font(size)
    value = str(value)
    bbox = d.textbbox((0, 0), value, font=f)
    d.text((int(x-(bbox[2]-bbox[0])/2), y), value, font=f, fill=color)

def logo(team):
    ident = str(team.get("id", ""))
    if not ident:
        return None
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / (ident + ".png")
    if not path.exists():
        logos = team.get("logos") or []
        url = team.get("logo") or (logos[0].get("href") if logos else None)
        if not url:
            return None
        try:
            image = Image.open(io.BytesIO(fetch(url))).convert("RGBA")
            image.save(path)
        except Exception as exc:
            print("NHL logo unavailable:", ident, exc)
            return None
    try:
        image = Image.open(path).convert("RGBA")
        bbox = image.getchannel("A").point(
            lambda a: 255 if a > 12 else 0
        ).getbbox()
        if bbox:
            image = image.crop(bbox)
        image.thumbnail((42, 38), Image.Resampling.LANCZOS)
        return image
    except Exception:
        return None

def priority(event):
    state = event.get("status", {}).get("type", {}).get("state")
    return ({"in": 0, "pre": 1, "post": 2}.get(state, 3),
            event.get("date", ""))

def shots(competitor):
    for stat in competitor.get("statistics") or []:
        if str(stat.get("name", "")).lower() in (
            "shots", "shotsongoal", "shots on goal"
        ):
            return str(stat.get("displayValue", stat.get("value", "")))
    return None

def render(event):
    comp = event["competitions"][0]
    teams = comp["competitors"]
    away = next(c for c in teams if c.get("homeAway") == "away")
    home = next(c for c in teams if c.get("homeAway") == "home")
    status = event["status"]
    state = status["type"]["state"]
    situation = comp.get("situation") or {}

    img = Image.new("RGB", (128, 64), BG)
    d = ImageDraw.Draw(img)
    # HUB75 panel: keep text glyph edges pixel-sharp, not grayscale-antialiased.
    d.fontmode = "1"

    for c, x in ((away, 26), (home, 102)):
        icon = logo(c["team"])
        if icon:
            # Make full use of the team columns while preserving score space.
            img.paste(icon, (x-icon.width//2, 2), icon)
        else:
            center(d, x, 14, c["team"].get("abbreviation", "???"), 10)

        if state in ("in", "post"):
            center(d, x, 39, c.get("score", "0"), 18)
        else:
            center(d, x, 43, c["team"].get("abbreviation", "???"), 10)

    if state == "in":
        period = int(status.get("period") or 0)
        clock = status.get("displayClock") or ""
        period_text = (
            f"P{period}" if period <= 3
            else "OT" if period == 4 else "SO"
        )
        center(d, 64, 0, period_text, 9, GOLD)
        center(d, 64, 13, clock[:7], 11)

        away_shots = shots(away)
        home_shots = shots(home)
        if away_shots is not None and home_shots is not None:
            center(d, 64, 33, "SHOTS", 6, GOLD)
            center(d, 64, 43, f"{away_shots}-{home_shots}", 8)

        # Only show a power-play indicator when ESPN provides it.
        pp = situation.get("powerPlay") or situation.get("powerplay")
        if pp:
            center(d, 64, 55, "POWER PLAY", 6, GOLD)

    elif state == "post":
        detail = status["type"].get("shortDetail", "FINAL")
        if "SO" in detail.upper():
            label = "FINAL SO"
        elif "OT" in detail.upper():
            label = "FINAL OT"
        else:
            label = "FINAL"
        center(d, 64, 24, label, 8, GOLD)

    else:
        kickoff = datetime.fromisoformat(
            event["date"].replace("Z", "+00:00")
        ).astimezone(TZ)
        center(d, 64, 12, kickoff.strftime("%a").upper(), 9, GOLD)
        center(d, 64, 28,
               kickoff.strftime("%I:%M%p").lstrip("0"), 8)

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    img.save(OUTPUT)
    print("NHL:", event.get("name", "Game"))
    print("Preview:", OUTPUT)
