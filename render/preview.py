from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
from PIL import Image, ImageDraw, ImageFont

W, H = 64, 32


def font():
    return ImageFont.load_default()


def load_asset(path, size=(18, 12)):
    p = Path(path)
    if not p.exists():
        return None
    img = Image.open(p).convert("RGB")
    return img.resize(size)


def status_text(game, mode, settings):
    tz = ZoneInfo(settings.get("timezone", "America/Los_Angeles"))
    now = datetime.now(tz)
    start = game.start_time.astimezone(tz)

    if game.status == "in":
        detail = game.detail or "LIVE"
        if "+" in detail:
            return "+" + detail.split("+", 1)[1].replace("'", "") + "'"
        return detail[:4]

    if game.status == "post":
        return "FT"

    delta = start - now
    mins = int(delta.total_seconds() // 60)

    if mins < 0:
        return "SOON"
    if mins < 60:
        return str(mins)
    if mins < 24 * 60:
        return f"{mins//60}H"
    return start.strftime("%a").upper()[:3]


def score_or_dash(score):
    return "-" if score is None else str(score)


def draw_centered(draw, box, text, fill, font_obj):
    x1, y1, x2, y2 = box
    bbox = draw.textbbox((0, 0), text, font=font_obj)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    x = x1 + ((x2 - x1 - tw) // 2)
    y = y1 + ((y2 - y1 - th) // 2)
    draw.text((x, y), text, fill=fill, font=font_obj)


def paste_flag(img, draw, asset, x, y, fallback_box):
    if asset:
        if any(pixel == (0, 0, 0) for pixel in asset.getdata()):
            draw.rectangle(
                [x - 1, y - 1, x + asset.width, y + asset.height],
                outline=(35, 35, 35)
            )
        img.paste(asset, (x, y))
    else:
        draw.rectangle(fallback_box, outline=(255, 255, 255))


def render_game(game, mode, settings, output_path):
    img = Image.new("RGB", (W, H), "black")
    d = ImageDraw.Draw(img)
    f = font()

    away_asset = load_asset(game.away.asset_path)
    home_asset = load_asset(game.home.asset_path)

    # Flags stay fixed.
    paste_flag(img, d, away_asset, 1, 2, [1, 2, 18, 14])
    paste_flag(img, d, home_asset, 45, 2, [45, 2, 62, 14])

    center = status_text(game, mode, settings)

    # Text shifted 2px left from original tuned layout.
    draw_centered(d, (20, 2, 27, 13), score_or_dash(game.away.score), (255, 255, 255), f)
    draw_centered(d, (26, 2, 39, 13), center, (255, 220, 0), f)
    draw_centered(d, (39, 2, 46, 13), score_or_dash(game.home.score), (255, 255, 255), f)

    draw_centered(d, (2, 18, 20, 29), game.away.abbr[:3], (255, 255, 255), f)
    draw_centered(d, (47, 18, 61, 29), game.home.abbr[:3], (255, 255, 255), f)

    # No bottom kickoff/worldcup text for now. Keeps countdown clean.

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path)
    return output_path


def render_test_pattern(output_path):
    img = Image.new("RGB", (W, H), "black")
    d = ImageDraw.Draw(img)
    colors = [(255,0,0), (0,255,0), (0,0,255), (255,255,255)]
    for i, c in enumerate(colors):
        d.rectangle([i*16, 0, i*16+15, 31], fill=c)
    d.rectangle([0,0,63,31], outline=(255,255,255))
    d.line([0,0,63,31], fill=(255,255,0))
    d.line([63,0,0,31], fill=(255,255,0))
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path)
    return output_path
