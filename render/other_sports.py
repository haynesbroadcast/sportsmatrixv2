"""Native 128x64 renderers for NBA, WNBA, MLB, MLS, NWSL and EPL.

Use clear pixel text, black background and centered two-team compositions.
The center information differs by sport. Unknown statistics are omitted,
never displayed as invented zeroes.
"""
import io
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import requests
from PIL import Image, ImageColor, ImageDraw, ImageFont
from render.pixel_font import center_text as bitmap_center

BASE = Path(__file__).resolve().parent.parent
CACHE = BASE / "assets" / "other_leagues"
OUTPUT = BASE / "output" / "other_sports.png"
PT = ZoneInfo("America/Los_Angeles")
WHITE, GOLD, DIM = "#f5f6f8", "#e9c56c", "#718092"
FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"
SPORT = {
    "nba": "basketball", "wnba": "basketball",
    "mlb": "baseball",
    "mls": "soccer", "nwsl": "soccer", "epl": "soccer",
}


def centered(draw, x, y, value, size, color=WHITE, max_width=None):
    value = str(value)
    f = ImageFont.truetype(FONT_PATH, size)
    if max_width is not None:
        while size > 7 and draw.textbbox((0, 0), value, font=f)[2] > max_width:
            size -= 1
            f = ImageFont.truetype(FONT_PATH, size)
    bbox = draw.textbbox((0, 0), value, font=f)
    draw.text((round(x - (bbox[2] - bbox[0]) / 2), y), value, fill=color, font=f)


def logo(team, league):
    ident = str(team.get("id") or team.get("abbreviation") or "")
    if not ident:
        return None
    path = CACHE / league / (ident.replace("/", "_") + ".png")
    try:
        if path.exists():
            raw = path.read_bytes()
        else:
            urls = team.get("logos") or []
            url = team.get("logo") or (urls[0].get("href") if urls else None)
            if not isinstance(url, str) or not url.startswith("https://"):
                return None
            response = requests.get(url, timeout=5,
                                    headers={"User-Agent": "SportsMatrixV2/0.11"})
            response.raise_for_status()
            raw = response.content
            CACHE.joinpath(league).mkdir(parents=True, exist_ok=True)
            Image.open(io.BytesIO(raw)).convert("RGBA").save(path)
        image = Image.open(io.BytesIO(raw)).convert("RGBA")
        bbox = image.getchannel("A").point(lambda a: 255 if a > 12 else 0).getbbox()
        if bbox:
            image = image.crop(bbox)
        image.thumbnail((37, 29), Image.Resampling.LANCZOS)
        return image
    except (OSError, ValueError, requests.RequestException):
        return None


def competitors(event):
    comps = event.get("competitions") or [{}]
    comp = comps[0]
    entries = comp.get("competitors") or []
    away = next((c for c in entries if c.get("homeAway") == "away"), entries[0] if entries else {})
    home = next((c for c in entries if c.get("homeAway") == "home"), entries[-1] if entries else {})
    return comp, away, home


def score_of(team, state):
    value = team.get("score")
    if state == "pre":
        return None
    return str(value) if value is not None and str(value) != "" else "-"


def _period(period, sport):
    try:
        period = int(period)
    except (TypeError, ValueError):
        return "LIVE"
    if sport == "basketball" or sport == "lacrosse":
        return f"Q{period}" if 0 < period <= 4 else "OT"
    if sport == "hockey":
        return f"P{period}" if 0 < period <= 3 else "OT" if period == 4 else "SO"
    if sport == "baseball":
        return f"IN{period}" if period > 0 else "LIVE"
    return "LIVE"


def _soccer_minute(event):
    status = event.get("status") or {}
    detail = str(status.get("type", {}).get("shortDetail") or "")
    clock = str(status.get("displayClock") or "").strip()
    if "+" in detail:
        return detail[:8]
    if clock and clock not in ("0:00", "00:00"):
        return clock[:7]
    return detail[:8] if detail else "LIVE"


def _baseball(draw, comp):
    situation = comp.get("situation") or {}
    # The ESPN scoreboard usually provides explicit occupied-base booleans.
    on_first = situation.get("onFirst")
    on_second = situation.get("onSecond")
    on_third = situation.get("onThird")
    if any(v is not None for v in (on_first, on_second, on_third)):
        for (cx, cy, occupied) in ((69, 39, on_first), (64, 34, on_second), (59, 39, on_third)):
            color = GOLD if occupied else DIM
            draw.polygon([(cx,cy-2),(cx+2,cy),(cx,cy+2),(cx-2,cy)], fill=color)
    outs = situation.get("outs")
    if outs is not None:
        centered(draw, 64, 45, f"{outs} OUT", 8, GOLD, 43)


def _context(image, draw, event, comp, away, home, sport, state):
    status = event.get("status") or {}
    if state == "post":
        detail = str(status.get("type", {}).get("shortDetail") or "FINAL")
        bitmap_center(image, 64, 14, "FINAL", GOLD)
        if "OT" in detail.upper() or "SO" in detail.upper():
            bitmap_center(image, 64, 28, "SO" if "SO" in detail.upper() else "OT", GOLD)
        return
    if state != "in":
        try:
            start = datetime.fromisoformat(event["date"].replace("Z", "+00:00")).astimezone(PT)
            bitmap_center(image, 64, 6, start.strftime("%a").upper(), GOLD)
            centered(draw, 64, 24, start.strftime("%I:%M%p").lstrip("0"), 8, WHITE, 42)
        except (KeyError, ValueError, TypeError):
            bitmap_center(image, 64, 16, "NEXT", GOLD)
        return
    if sport == "soccer":
        bitmap_center(image, 64, 3, "MATCH", GOLD)
        centered(draw, 64, 18, _soccer_minute(event), 10, WHITE, 44)
        return
    period = _period(status.get("period"), sport)
    bitmap_center(image, 64, 3, period, GOLD)
    clock = str(status.get("displayClock") or "")[:8]
    if clock and clock not in ("0:00", "00:00"):
        centered(draw, 64, 17, clock, 11, WHITE, 42)
    if sport == "baseball":
        # Bottom half shown by a small downward triangle. Top is upward.
        situation = comp.get("situation") or {}
        if situation.get("isBottomInning") is not None:
            if situation["isBottomInning"]:
                draw.polygon([(63,30),(67,30),(65,33)], fill=GOLD)
            else:
                draw.polygon([(63,33),(67,33),(65,30)], fill=GOLD)
        _baseball(draw, comp)
    elif sport == "hockey":
        def shots(team):
            for stat in team.get("statistics") or []:
                if str(stat.get("name", "")).replace(" ", "").lower() in ("shots", "shotsongoal"):
                    return str(stat.get("displayValue", stat.get("value", "")))
            return None
        a, h = shots(away), shots(home)
        if a is not None and h is not None:
            bitmap_center(image, 64, 34, "SHOTS", GOLD)
            centered(draw, 64, 44, f"{a}-{h}", 8, WHITE, 42)


def render(event, league, output_path=None, *, sample=False):
    if league not in SPORT:
        raise ValueError("Unsupported sport renderer: " + str(league))
    output_path = Path(output_path or OUTPUT)
    if league == "mlb":
        from render.mlb_board import render_mlb
        return render_mlb(event, output_path, sample=sample)
    sport = SPORT[league]
    comp, away, home = competitors(event)
    state = event.get("status", {}).get("type", {}).get("state", "pre")
    image = Image.new("RGB", (128, 64), "#000000")
    draw = ImageDraw.Draw(image)
    draw.fontmode = "1"

    for team, x in ((away, 26), (home, 102)):
        details = team.get("team") or {}
        icon = logo(details, league)
        if icon:
            image.paste(icon, (x - icon.width // 2, 2), icon)
        else:
            abbr = str(details.get("abbreviation") or details.get("shortDisplayName") or "???")[:4]
            centered(draw, x, 10, abbr, 11, WHITE, 44)
        score = score_of(team, state)
        if score is not None:
            centered(draw, x, 34, score, 26 if sport == "basketball" else 27, WHITE, 48)
        else:
            abbr = str(details.get("abbreviation") or details.get("shortDisplayName") or "???")[:4]
            centered(draw, x, 37, abbr, 10, WHITE, 44)

    _context(image, draw, event, comp, away, home, sport, state)
    if sample:
        bitmap_center(image, 64, 56, "SAMPLE", DIM)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(output_path)
    return output_path


def render_no_games(league, output_path=None):
    """An explicit empty-season state, never a fictional matchup or stale frame."""
    if league not in SPORT:
        raise ValueError("Unsupported league: " + str(league))
    output_path = Path(output_path or OUTPUT)
    image = Image.new("RGB", (128, 64), "#000000")
    draw = ImageDraw.Draw(image)
    draw.fontmode = "1"
    label = {"epl": "EPL", "nwsl": "NWSL", "mls": "MLS",
             "nba": "NBA",
             "wnba": "WNBA", "mlb": "MLB"}[league]
    bitmap_center(image, 64, 4, label, GOLD)
    centered(draw, 64, 24, "NO GAMES", 13, WHITE, 110)
    bitmap_center(image, 64, 47, "CHECK LATER", DIM)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(output_path)
    return output_path
