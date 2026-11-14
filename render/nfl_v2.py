import io
import json
import sys
import urllib.request
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
from PIL import Image, ImageDraw, ImageFont

BASE = Path(__file__).resolve().parent.parent
CACHE = BASE / "assets/nfl"
OUTPUT = BASE / "output/nfl_v2.png"
API = ("https://site.api.espn.com/apis/site/v2/"
       "sports/football/nfl/scoreboard"
       "?limit=100")
TZ = ZoneInfo("America/Los_Angeles")
GOLD, WHITE, DIM = "#e9c56c", "#f5f6f8", "#344253"

def fetch(url):
    req = urllib.request.Request(
        url, headers={"User-Agent": "SportsMatrixV2/1.0"})
    with urllib.request.urlopen(req, timeout=15) as r:
        return r.read()

def font(size):
    return ImageFont.truetype(
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", size)

def center(d, x, y, text, size, color=WHITE):
    f = font(size)
    box = d.textbbox((0, 0), str(text), font=f)
    d.text((int(x-(box[2]-box[0])/2), y), str(text),
           font=f, fill=color)

def rank(c):
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
        except Exception as exc:
            print("NFL logo unavailable:", team_id, exc)
            return None

    try:
        image = Image.open(path).convert("RGBA")

        # Remove transparent padding around actual team artwork.
        alpha = image.getchannel("A")
        bbox = alpha.point(lambda a: 255 if a > 12 else 0).getbbox()
        if bbox:
            image = image.crop(bbox)

        image.thumbnail((38, 32), Image.Resampling.LANCZOS)
        return image
    except Exception as exc:
        print("NFL logo processing failed:", team_id, exc)
        return None


def priority(event):
    state = event.get("status", {}).get("type", {}).get("state")
    order = {"in": 0, "pre": 1, "post": 2}
    return (order.get(state, 3), event.get("date", ""))



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
    possession = str(situation.get("possession", ""))

    for c, x in ((away, 26), (home, 102)):
        team = c["team"]
        icon = logo(team)

        if icon:
            icon.thumbnail((36, 31), Image.Resampling.LANCZOS)
            img.paste(icon, (x - icon.width // 2, 3), icon)
        else:
            center(d, x, 13, team.get("abbreviation", "???")[:4], 9)

        if state == "in" and possession == str(team.get("id", "")):
            # Compact football icon just below the logo.
            d.ellipse((x - 5, 30, x + 5, 35), fill=GOLD)
            d.line((x - 2, 32, x + 2, 32),
                   fill="#000000", width=1)
            d.line((x, 31, x, 34),
                   fill="#000000", width=1)

        if state in ("in", "post"):
            center(d, x, 39, str(c.get("score", "0")), 18)
        else:
            center(d, x, 43, team.get("abbreviation", "???")[:5], 10)

        if state == "in":
            key = (
                "awayTimeouts" if c["homeAway"] == "away"
                else "homeTimeouts"
            )
            remaining = situation.get(key)
            if remaining is not None:
                remaining = max(0, min(3, int(remaining)))
                for i in range(3):
                    left = x - 11 + i * 8
                    d.rectangle(
                        (left, 59, left + 5, 61),
                        fill=GOLD if i < remaining else DIM
                    )

    if state == "in":
        period = int(status.get("period") or 0)
        clock = status.get("displayClock", "")

        if period <= 4:
            period_text = f"Q{period}"
        else:
            period_text = f"OT{period - 4}"

        center(d, 64, 0, period_text, 9, GOLD)
        center(d, 64, 13, clock[:7], 11)

        down = situation.get("shortDownDistanceText")
        if not down and situation.get("down"):
            down = (
                f"{situation['down']} & "
                f"{situation.get('distance', '?')}"
            )

        if down:
            center(d, 64, 34, str(down).upper()[:12], 7)

        field = situation.get("possessionText")
        if field:
            center(d, 64, 47, str(field)[:12], 8, GOLD)

    elif state == "post":
        center(d, 64, 24, "FINAL", 10, GOLD)

    else:
        kickoff = datetime.fromisoformat(
            event["date"].replace("Z", "+00:00")
        ).astimezone(TZ)

        center(d, 64, 12, kickoff.strftime("%a").upper(), 9, GOLD)
        center(
            d, 64, 28,
            kickoff.strftime("%I:%M%p").lstrip("0"), 8
        )
        center(d, 64, 44, "PT", 7, DIM)

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    img.save(OUTPUT)
    print("NFL:", event["name"])
    print("Preview:", OUTPUT)

def main():
    data = json.loads(fetch(API))
    events = data.get("events", [])
    if not events:
        sys.exit("ESPN returned no games.")
    render(sorted(events, key=priority)[0])

if __name__ == "__main__":
    main()
