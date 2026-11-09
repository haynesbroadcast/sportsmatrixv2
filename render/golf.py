from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

WIDTH, HEIGHT = 128, 64
ROWS_PER_PAGE = 4
MAX_PAGES = 4

def _font(size=8):
    return ImageFont.truetype(
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        size
    )

def _theme(title):
    t = title.lower()
    if "masters" in t:
        return "#062e19", "#ffdf35", "#ffffff"
    if "u.s." in t or "us open" in t:
        return "#071327", "#e9e9ed", "#ffffff"
    if "open championship" in t or "british open" in t:
        return "#10251e", "#e5d5a3", "#ffffff"
    return "#091520", "#63d7bb", "#ffffff"

def _score_color(score):
    s = str(score).strip().upper()
    if s.startswith("-"):
        return "#b52c32"
    if s.startswith("+"):
        return "#050505"
    return "#263a47"

def _fit(draw, text, font, max_width):
    text = str(text)
    while text and draw.textbbox((0, 0), text, font=font)[2] > max_width:
        text = text[:-1]
    return text

def render_golf(board, settings, output_path, page=0):
    title = str(board.get("title") or "GOLF").upper()
    players = board.get("players") or []
    bg, accent, fg = _theme(title)

    img = Image.new("RGB", (WIDTH, HEIGHT), bg)
    d = ImageDraw.Draw(img)

    title_font = _font(8)
    row_font = _font(8)
    small_font = _font(7)

    pages = max(
        1,
        min(MAX_PAGES, (len(players) + ROWS_PER_PAGE - 1) // ROWS_PER_PAGE)
    )
    page = int(page) % pages
    rows = players[page * ROWS_PER_PAGE:(page + 1) * ROWS_PER_PAGE]

    round_num = board.get("round") or 0
    right_header = "R" + str(round_num) if round_num else "PGA"

    d.text((2, 1), _fit(d, title, title_font, 99), fill=accent, font=title_font)
    d.text((109, 1), right_header, fill=accent, font=small_font)
    d.line((1, 12, 126, 12), fill=accent, width=1)

    d.text((2, 14), "POS", fill="#8798a5", font=small_font)
    d.text((24, 14), "PLAYER", fill="#8798a5", font=small_font)
    d.text((84, 14), "THRU", fill="#8798a5", font=small_font)
    d.text((108, 14), "TOT", fill="#8798a5", font=small_font)

    for i, player in enumerate(rows):
        y = 24 + i * 10

        if i % 2 == 1:
            d.rectangle((0, y - 1, 127, y + 9), fill="#142633")

        position = str(player.get("position", i + 1))
        name = _fit(d, player.get("name", ""), row_font, 58)
        thru = str(player.get("thru", "--"))
        score = str(player.get("score", "E")).upper()

        d.text((2, y), position[:3], fill=fg, font=small_font)
        d.text((24, y - 1), name, fill=fg, font=row_font)
        d.text((87, y), thru[:3], fill=fg, font=small_font)

        d.rectangle((105, y - 1, 127, y + 8), fill=_score_color(score))
        bbox = d.textbbox((0, 0), score, font=small_font)
        sw = bbox[2] - bbox[0]
        d.text((116 - sw // 2, y), score[:4], fill="#ffffff", font=small_font)

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path)
    return pages
