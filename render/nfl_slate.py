"""Native 128x64 NFL pregame slate: three matchups per page.

Uses the ESPN team artwork already present in the NFL feed. Logo resizing is
alpha-aware and cached separately from the full-size NFL game renderer.
"""
import io
import math
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from PIL import Image, ImageColor, ImageDraw, ImageFilter

from .nfl_v2 import BASE, CACHE, fetch
from .pixel_font import draw_text, text_width

OUTPUT = BASE / "output" / "nfl_slate.png"
LOGO_CACHE = CACHE / "slate-v015"
PT = ZoneInfo("America/Los_Angeles")
SIZE = (128, 64)
PER_PAGE = 3
PAGE_SECONDS = 12


def _color(value, default):
    try:
        value = str(value or "").strip().lstrip("#")
        if len(value) != 6:
            return default
        return ImageColor.getrgb("#" + value)
    except ValueError:
        return default


def _competitors(event):
    teams = event["competitions"][0]["competitors"]
    return (next(t["team"] for t in teams if t["homeAway"] == "away"),
            next(t["team"] for t in teams if t["homeAway"] == "home"))


def _logo_source(team):
    logos = team.get("logos") or []
    return team.get("logo") or (logos[0].get("href") if logos else None)


def prepare_logo(image, width=22, height=17):
    """Trim transparent margins, fit without distortion, and tame subpixel halos."""
    image = image.convert("RGBA")
    alpha = image.getchannel("A")
    bbox = alpha.point(lambda a: 255 if a >= 18 else 0).getbbox()
    if bbox is None:
        return None
    image = image.crop(bbox)
    image.thumbnail((width, height), Image.Resampling.LANCZOS)
    # A light unsharp mask recovers one-pixel edges lost at 17px height.
    image = image.filter(ImageFilter.UnsharpMask(radius=0.55, percent=90, threshold=2))
    # Preserve antialiasing, but eliminate faint transparent fringe pixels.
    rgba = list(image.getdata())
    cleaned = []
    for r, g, b, a in rgba:
        if a < 30:
            cleaned.append((0, 0, 0, 0))
        elif a > 235:
            cleaned.append((r, g, b, 255))
        else:
            cleaned.append((r, g, b, round(a / 17) * 17))
    image.putdata(cleaned)
    return image


def team_logo(team):
    """Fetch each source once, cache a transparent panel-sized PNG, fallback safely."""
    team_id = str(team.get("id") or "")
    url = _logo_source(team)
    if not team_id or not url:
        return None
    path = LOGO_CACHE / (team_id + ".png")
    if path.exists():
        try:
            return Image.open(path).convert("RGBA")
        except (OSError, ValueError):
            path.unlink(missing_ok=True)
    try:
        image = prepare_logo(Image.open(io.BytesIO(fetch(url))))
        if image is None:
            return None
        LOGO_CACHE.mkdir(parents=True, exist_ok=True)
        image.save(path)
        return image
    except (OSError, ValueError, TimeoutError) as exc:
        print("NFL slate logo unavailable:", team_id, exc)
        return None


def _gradient(image, y0, away, home):
    pixels = image.load()
    a = _color(away.get("color"), (20, 62, 125))
    b = _color(home.get("color"), (110, 40, 35))
    for y in range(y0, min(y0 + 20, 63)):
        for x in range(12, 128):
            # Slight diagonal drift, no hard color-block boundary.
            t = max(0.0, min(1.0, (x - 12 + (y - y0 - 10) * 0.45) / 116))
            t = t * t * (3 - 2 * t)
            shade = 0.38 + 0.05 * math.cos((y - y0 - 10) / 12)
            pixels[x, y] = tuple(round((a[i] * (1 - t) + b[i] * t) * shade) for i in range(3))


def _rotated_time(image, events, page, total):
    strip = Image.new("RGB", (11, 64), "#03070e")
    first = datetime.fromisoformat(events[0]["date"].replace("Z", "+00:00")).astimezone(PT)
    hour = first.strftime("%I").lstrip("0")
    if first.minute:
        # Compact 1030A / 130P form preserves the day at native resolution.
        clock = f"{hour}{first.minute:02d}{first.strftime('%p')[0]}"
    else:
        clock = f"{hour}{first.strftime('%p')}"
    label = first.strftime("%a").upper() + " " + clock  # SUN 10AM
    # Rotate native bitmap text: 8 chars use 47 vertical pixels.
    flat = Image.new("RGB", (text_width(label) + 2, 7), "#03070e")
    draw_text(flat, 1, 0, label, (245, 245, 245))
    turned = flat.transpose(Image.Transpose.ROTATE_90)
    strip.paste(turned, (2, 3))
    for index in range(min(total, 3)):
        ImageDraw.Draw(strip).rectangle((2 + index * 3, 61, 3 + index * 3, 62),
                                       fill="#ffffff" if index == page else "#3b4b61")
    image.paste(strip, (0, 0))


def _place_logo(image, team, x, y):
    icon = team_logo(team)
    if icon is None:
        return False
    layer = Image.new("RGBA", SIZE, (0, 0, 0, 0))
    layer.paste(icon, (x + (22 - icon.width) // 2, y + (17 - icon.height) // 2))
    image.alpha_composite(layer)
    return True


def render_slate(events, page=0, output=OUTPUT):
    """Render one page of a pregame broadcast window to an exact 128x64 PNG."""
    if not events:
        raise ValueError("Cannot render an empty NFL slate")
    pages = max(1, (len(events) + PER_PAGE - 1) // PER_PAGE)
    page %= pages
    subset = events[page * PER_PAGE:(page + 1) * PER_PAGE]
    image = Image.new("RGB", SIZE, "#000000")
    for index, event in enumerate(subset):
        away, home = _competitors(event)
        _gradient(image, index * 21, away, home)
    _rotated_time(image, events, page, pages)
    rgba = image.convert("RGBA")
    logo_ok = []
    for index, event in enumerate(subset):
        away, home = _competitors(event)
        y = index * 21
        logo_ok.append((_place_logo(rgba, away, 13, y + 2),
                        _place_logo(rgba, home, 94, y + 2)))
    image = rgba.convert("RGB")
    d = ImageDraw.Draw(image)
    for index, event in enumerate(subset):
        away, home = _competitors(event)
        y = index * 21
        if not logo_ok[index][0]:
            draw_text(image, 16, y + 7, away.get("abbreviation", "???")[:3], (255, 255, 255))
        if not logo_ok[index][1]:
            draw_text(image, 96, y + 7, home.get("abbreviation", "???")[:3], (255, 255, 255))
        # Pixel shadow instead of the v0.15 solid black acronym boxes.
        # Keep gradients continuous behind the text.
        draw_text(image, 38, y + 7, away.get("abbreviation", "???")[:3], (4, 8, 14))
        draw_text(image, 73, y + 7, home.get("abbreviation", "???")[:3], (4, 8, 14))
        draw_text(image, 59, y + 7, "AT", (4, 8, 14))
        draw_text(image, 37, y + 6, away.get("abbreviation", "???")[:3], (255, 255, 255))
        draw_text(image, 72, y + 6, home.get("abbreviation", "???")[:3], (255, 255, 255))
        draw_text(image, 58, y + 6, "AT", (236, 196, 113))
        if index < 2:
            d.line((12, y + 20, 127, y + 20), fill=(84, 91, 108))
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    image.save(output)
    return image
