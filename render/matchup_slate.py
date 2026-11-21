"""Reusable native 128x64 pregame pages for non-NFL team sports.

The NFL v0.17 renderer is intentionally unchanged. This module applies its
successful three-up gradient, transparent-logo and standalone-feature
principles to NHL, college football, basketball and soccer. Live and final
games always use their score-first league renderer.
"""
import math
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from PIL import Image, ImageDraw

from .logo_contrast import composite_logo
from .pixel_font import center_text, draw_text
from .nfl_slate import _color, _rotated_time, prepare_logo

BASE = Path(__file__).resolve().parent.parent
PT = ZoneInfo("America/Los_Angeles")
SIZE = (128, 64)
PER_PAGE = 3
PAGE_SECONDS = 12
LEAGUES = frozenset(("nhl", "cfb", "nba", "wnba", "mls", "nwsl", "epl"))


def _teams(event):
    entries = event["competitions"][0]["competitors"]
    away = next(c["team"] for c in entries if c.get("homeAway") == "away")
    home = next(c["team"] for c in entries if c.get("homeAway") == "home")
    return away, home


def _logo(team, league):
    # Use the appropriate league cache, never NFL artwork or an invented logo.
    if league == "nhl":
        from .nhl_v2 import logo
        return logo(team)
    if league == "cfb":
        from .cfb_v2 import logo
        return logo(team)
    from .other_sports import logo
    return logo(team, league)


def _gradient(image, top, away, home, height=20):
    pixels = image.load()
    left = _color(away.get("color"), (24, 67, 135))
    right = _color(home.get("color"), (115, 49, 67))
    for y in range(top, min(top + height, 64)):
        for x in range(12, 128):
            t = max(0.0, min(1.0, (x - 12 + (y - top - height / 2) * .45) / 116))
            t = t * t * (3 - 2 * t)
            shade = .38 + .05 * math.cos((y - top - height / 2) / 12)
            pixels[x, y] = tuple(round((left[i] * (1 - t) + right[i] * t) * shade)
                                 for i in range(3))


def _small_logo(canvas, team, league, x, y):
    icon = _logo(team, league)
    if icon is None:
        return False
    icon = prepare_logo(icon, 22, 17)
    if icon is None:
        return False
    return composite_logo(canvas, icon, x + (22 - icon.width) // 2,
                          y + (17 - icon.height) // 2)


def render_slate(events, league, page=0, output_path=None):
    """Render three pregame games per page; sparse overflow remains a slate."""
    if league not in LEAGUES:
        raise ValueError("Unsupported matchup slate: " + str(league))
    if not events:
        raise ValueError("Cannot render an empty slate")
    count = max(1, (len(events) + PER_PAGE - 1) // PER_PAGE)
    page %= count
    subset = events[page * PER_PAGE:(page + 1) * PER_PAGE]
    offset = (PER_PAGE - len(subset)) * 21 // 2
    image = Image.new("RGB", SIZE, "#000000")
    for index, event in enumerate(subset):
        away, home = _teams(event)
        _gradient(image, offset + index * 21, away, home)
    _rotated_time(image, events, page, count)

    canvas = image.convert("RGBA")
    found = []
    for index, event in enumerate(subset):
        away, home = _teams(event)
        y = offset + index * 21
        found.append((_small_logo(canvas, away, league, 13, y + 2),
                      _small_logo(canvas, home, league, 94, y + 2)))
    image = canvas.convert("RGB")
    draw = ImageDraw.Draw(image)
    for index, event in enumerate(subset):
        away, home = _teams(event)
        y = offset + index * 21
        if not found[index][0]:
            draw_text(image, 16, y + 7, away.get("abbreviation", "???")[:3], "#ffffff")
        if not found[index][1]:
            draw_text(image, 96, y + 7, home.get("abbreviation", "???")[:3], "#ffffff")
        for x, label, color in (
                (37, away.get("abbreviation", "???")[:3], "#ffffff"),
                (58, "AT", "#ecc471"),
                (72, home.get("abbreviation", "???")[:3], "#ffffff")):
            draw_text(image, x + 1, y + 7, label, "#04080e")
            draw_text(image, x, y + 6, label, color)
        if index < len(subset) - 1:
            draw.line((12, y + 20, 127, y + 20), fill=(84, 91, 108))

    output = Path(output_path or BASE / "output" / f"{league}_slate.png")
    output.parent.mkdir(parents=True, exist_ok=True)
    image.save(output)
    return image


def render_feature(event, league, output_path=None):
    """Single-game pregame graphic; no scores or live-game information hidden."""
    if league not in LEAGUES:
        raise ValueError("Unsupported feature sport: " + str(league))
    away, home = _teams(event)
    image = Image.new("RGB", SIZE, "#000000")
    pixels = image.load()
    left = _color(away.get("color"), (24, 67, 135))
    right = _color(home.get("color"), (115, 49, 67))
    for y in range(64):
        for x in range(128):
            t = max(0.0, min(1.0, (x + (y - 32) * .30) / 127))
            t = t * t * (3 - 2 * t)
            shade = .40 if y < 40 else .23
            pixels[x, y] = tuple(round((left[i] * (1 - t) + right[i] * t) * shade)
                                 for i in range(3))
    canvas = image.convert("RGBA")
    for team, x in ((away, 8), (home, 82)):
        icon = _logo(team, league)
        if icon is None:
            continue
        icon = icon.copy().convert("RGBA")
        alpha = icon.getchannel("A")
        bbox = alpha.point(lambda a: 255 if a > 12 else 0).getbbox()
        if not bbox:
            continue
        icon = icon.crop(bbox)
        icon.thumbnail((38, 32), Image.Resampling.LANCZOS)
        composite_logo(canvas, icon, x + (38 - icon.width) // 2,
                       7 + (32 - icon.height) // 2)
    image = canvas.convert("RGB")
    draw = ImageDraw.Draw(image)
    draw.line((0, 40, 127, 40), fill=(93, 100, 115))
    start = datetime.fromisoformat(event["date"].replace("Z", "+00:00")).astimezone(PT)
    hour = start.strftime("%I").lstrip("0")
    clock = f"{hour}:{start.minute:02d}" if start.minute else hour
    clock += start.strftime("%p")
    center_text(image, 64, 3, start.strftime("%A").upper(), (218, 196, 138))
    center_text(image, 64, 23, "VS", (245, 246, 249))
    center_text(image, 27, 47, away.get("abbreviation", "???")[:3], "#ffffff")
    center_text(image, 101, 47, home.get("abbreviation", "???")[:3], "#ffffff")
    center_text(image, 64, 43, start.strftime("%a").upper(), (231, 196, 122))
    center_text(image, 64, 54, clock, "#ffffff")
    if league == "cfb":
        from .cfb_v2 import rank
        for entry, x in ((next(c for c in event["competitions"][0]["competitors"]
                                if c["homeAway"] == "away"), 27),
                         (next(c for c in event["competitions"][0]["competitors"]
                                if c["homeAway"] == "home"), 101)):
            n = rank(entry)
            if n:
                center_text(image, x, 0, f"#{n}", (231, 196, 122))

    output = Path(output_path or BASE / "output" / f"{league}_feature.png")
    output.parent.mkdir(parents=True, exist_ok=True)
    image.save(output)
    return image
