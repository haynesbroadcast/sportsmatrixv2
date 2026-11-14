"""Score-first MLB display, composed natively at exactly 128x64 pixels.

Layout: baseball state top (0-19), small R/H/E header (20-27),
two 18-pixel team rows (28-45 and 46-63). No logos, inning grid, or
decorative padding. Every divider is one source pixel.
"""
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
from PIL import Image, ImageDraw, ImageFont

from .pixel_font import center_text as pixels

FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"
PT = ZoneInfo("America/Los_Angeles")
WHITE = (248, 249, 250)
GOLD = (245, 202, 100)
MUTED = (90, 103, 123)
BLACK = (0, 0, 0)
DEFAULT_TEAM_COLORS = {"LAD": (0, 65, 138), "SF": (253, 90, 30)}

def _font(size):
    return ImageFont.truetype(FONT, size)

def _rgb(hexvalue):
    if not isinstance(hexvalue, str):
        return None
    digits = hexvalue.lstrip("#")
    if len(digits) != 6:
        return None
    try:
        return tuple(int(digits[i:i+2], 16) for i in (0, 2, 4))
    except ValueError:
        return None

def _shade(color, factor):
    return tuple(max(0, min(255, round(x * factor))) for x in color)

def _ink(background):
    # Contrast of the overall tinted panel background, rather than arbitrary
    # brand-specific assumptions about which teams use dark/light primary colors.
    return BLACK if sum(0.2126 * c for c in background[:1]) + 0.7152*background[1] + 0.0722*background[2] > 155 else WHITE

def team_color(team):
    abbr = _abbr(team)
    provider = team.get("team") or {}
    return DEFAULT_TEAM_COLORS.get(abbr) or _rgb(provider.get("color")) or (35, 59, 87)

def _abbr(entry):
    team = entry.get("team") or {}
    value = str(team.get("abbreviation") or team.get("shortDisplayName") or "???").upper()
    # SF is the canonical abbreviation used on this display, not SFG.
    return "SF" if value == "SFG" else value[:3]

def _text(draw, text, x1, y, x2, size, color, minimum=7):
    value = str(text)
    font = _font(size)
    bbox = draw.textbbox((0, 0), value, font=font)
    while bbox[2] - bbox[0] > x2-x1 and size > minimum:
        size -= 1
        font = _font(size)
        bbox = draw.textbbox((0, 0), value, font=font)
    x = round(x1 + (x2 - x1 - (bbox[2] - bbox[0]))/2)
    # textbbox top is positive with DejaVu; normalize to requested top row
    draw.text((x, y-bbox[1]), value, font=font, fill=color)

def _stat(entry, names):
    for item in entry.get("statistics") or []:
        key = str(item.get("name") or item.get("abbreviation") or item.get("label") or "").lower().replace(" ", "")
        if key in names:
            value = item.get("displayValue")
            if value is None:
                value = item.get("value")
            if value is not None and str(value) != "":
                return str(value)
    return None

def _rhe(entry, state):
    if state == "pre":
        return ("-", "-", "-")
    runs = entry.get("score")
    return (
        str(runs) if runs is not None and str(runs) != "" else "-",
        _stat(entry, {"hits", "h"}),
        _stat(entry, {"errors", "e"}),
    )

def _challenge_count(entry, situation):
    # Different live MLB feed versions attach remaining challenges to
    # the competition or competitor. Unknown means two neutral indicators,
    # not an invented count of remaining challenges.
    for key in ("challengesRemaining", "remainingChallenges"):
        value = entry.get(key)
        if value is None:
            value = situation.get(key)
        if value is not None:
            try:
                return max(0, min(2, int(value)))
            except (TypeError, ValueError):
                pass
    return None

def _base_value(situation, key):
    value = situation.get(key)
    if isinstance(value, dict):
        return True
    if value is None:
        return None
    if isinstance(value, str):
        return value.lower() not in ("false", "0", "none", "")
    return bool(value)

def _diamond(draw, situation):
    for x,y,key in ((118, 10, "onFirst"), (112, 4, "onSecond"), (106, 10, "onThird")):
        occupied = _base_value(situation, key)
        fill = GOLD if occupied else (45, 56, 69)
        draw.polygon([(x,y-3),(x+3,y),(x,y+3),(x-3,y)], fill=fill)

def _header(image, draw, event, comp):
    state = event.get("status", {}).get("type", {}).get("state", "pre")
    status = event.get("status") or {}
    situation = comp.get("situation") or {}
    if state == "in":
        inning = status.get("period") or situation.get("inning") or "?"
        bottom = situation.get("isBottomInning")
        detail = str(status.get("type", {}).get("shortDetail") or "").upper()
        # ESPN shortDetail can say 'Top 7th' even when situation does not
        # explicitly expose a bottom-half boolean.
        half = "BOT" if bottom is True or (bottom is None and ("BOT" in detail or "BOTTOM" in detail)) else "TOP"
        _text(draw, half, 0, 1, 29, 11, WHITE)
        _text(draw, str(inning), 28, 0, 44, 17, GOLD)
        for label, x, key, maxval in (("B", 49, "balls", 3), ("S", 71, "strikes", 2), ("O", 93, "outs", 3)):
            pixels(image, x+3, 1, label, GOLD)
            count = situation.get(key)
            val = "-" if count is None else str(count)
            _text(draw, val, x, 9, x+14, 10, WHITE)
        _diamond(draw, situation)
    elif state == "post":
        _text(draw, "FINAL", 0, 1, 60, 15, GOLD)
        detail = str(status.get("type", {}).get("shortDetail") or "")
        if "EXTRA" in detail.upper():
            _text(draw, "EXTRAS", 67, 5, 112, 8, WHITE)
    else:
        _text(draw, "NEXT", 1, 2, 40, 13, GOLD)
        try:
            start = datetime.fromisoformat(event["date"].replace("Z", "+00:00")).astimezone(PT)
            _text(draw, start.strftime("%a").upper(), 47, 2, 78, 10, WHITE)
            _text(draw, start.strftime("%I:%M%p").lstrip("0"), 78, 2, 127, 9, WHITE)
        except (KeyError, ValueError, TypeError):
            pass

def draw_board(event, *, sample=False):
    comp = (event.get("competitions") or [{}])[0]
    competitors = comp.get("competitors") or []
    away = next((t for t in competitors if t.get("homeAway")=="away"), competitors[0] if competitors else {})
    home = next((t for t in competitors if t.get("homeAway")=="home"), competitors[-1] if competitors else {})
    situation = comp.get("situation") or {}
    state = event.get("status", {}).get("type", {}).get("state", "pre")
    image = Image.new("RGB", (128, 64), BLACK)
    draw = ImageDraw.Draw(image)
    draw.fontmode = "1"
    _header(image, draw, event, comp)

    # R takes the largest column, with two smaller H/E columns.
    # Header is only 8 px tall and no decorative perimeter frame.
    draw.rectangle((0, 20, 127, 27), fill=(24, 32, 44))
    for label, xl, xr in (("R", 71, 94), ("H", 95, 110), ("E", 111, 127)):
        pixels(image, (xl+xr)//2, 20, label, GOLD)
    draw.line((0, 27, 127, 27), fill=MUTED)

    for entry, top in ((away, 28), (home, 46)):
        base = team_color(entry)
        light = _shade(base, 0.85)
        dark = _shade(base, 0.54)
        label_bg = _shade(base, 0.68)
        run_bg = _shade(base, 1.55)
        hit_bg = _shade(base, 0.80)
        err_bg = _shade(base, 0.65)
        draw.rectangle((0, top, 70, top+17), fill=label_bg)
        draw.rectangle((71, top, 94, top+17), fill=run_bg)
        draw.rectangle((95, top, 110, top+17), fill=hit_bg)
        draw.rectangle((111, top, 127, top+17), fill=err_bg)
        # One pixel dividers only.
        for xx in (70, 94, 110):
            draw.line((xx, top, xx, top+17), fill=BLACK)
        if top == 46:
            draw.line((0, 46, 127, 46), fill=BLACK)
        _text(draw, _abbr(entry), 2, top+2, 43, 14, _ink(label_bg))
        # Two challenge dots per team, centered in the name region.
        remaining = _challenge_count(entry, situation)
        for i, px in enumerate((51, 61)):
            fill = GOLD if remaining is not None and i < remaining else (
                _shade(GOLD, .20) if remaining is not None else WHITE)
            draw.ellipse((px-2, top+7, px+1, top+10), fill=fill)
        runs, hits, errs = _rhe(entry, state)
        _text(draw, runs, 72, top+1, 94, 17, _ink(run_bg))
        _text(draw, hits if hits is not None else "-", 95, top+3, 110, 12, _ink(hit_bg))
        _text(draw, errs if errs is not None else "-", 111, top+3, 127, 12, _ink(err_bg))
    if sample:
        # In the footer corner rather than covering score. Actual live frames
        # do not carry a demo watermark.
        pixels(image, 64, 13, "*", MUTED)
    return image

def render_mlb(event, path, *, sample=False):
    image = draw_board(event, sample=sample)
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    image.save(destination)
    return destination
