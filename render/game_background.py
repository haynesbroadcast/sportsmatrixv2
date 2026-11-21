"""Team-color live/final game backdrop shared across score-first renderers.

The pregame NFL and cross-sport features established the visual language:
away-to-home diagonal fade, subdued team colors and contrast-aware logos.
This variation reserves a dark center spine for clocks and situation data
and darkens the lower score area, without moving or covering any glyphs.
"""
import math

from PIL import Image, ImageColor

SIZE = (128, 64)
AWAY_FALLBACK = (24, 67, 135)
HOME_FALLBACK = (115, 49, 67)


def _color(value, fallback):
    if not isinstance(value, str):
        return fallback
    digits = value.strip().lstrip("#")
    if len(digits) != 6:
        return fallback
    try:
        return ImageColor.getrgb("#" + digits)
    except ValueError:
        return fallback


def game_background(away, home, state="in"):
    """Return a native 128x64 RGB team-color gradient for live/final games.

    Both team colors come from the same ESPN team fields as the pregame
    feature. The center information column stays dark, even when both
    teams have bright colors. Postgame uses the same palette but is
    slightly quieter. There are no score-dependent decorative effects.
    """
    if state not in ("in", "post"):
        raise ValueError("Game gradient is only for live/final screens")
    left = _color((away or {}).get("color"), AWAY_FALLBACK)
    right = _color((home or {}).get("color"), HOME_FALLBACK)
    image = Image.new("RGB", SIZE)
    pixels = image.load()
    for y in range(64):
        for x in range(128):
            t = max(0.0, min(1.0, (x + (y - 32) * .30) / 127))
            t = t * t * (3 - 2 * t)
            # Similar saturation and direction to pregame, but slightly
            # darker beneath the large live score numerals.
            shade = .43 if y < 34 else .29
            if state == "post":
                shade *= .86
            # Center clock/down-distance/shots text remains high contrast.
            # Smooth rolloff, not a hard vertical black rectangle.
            distance = abs(x - 64)
            spine = .58 + .42 * min(1.0, (distance / 27) ** 1.6)
            # A little texture, still pixel-stable from refresh to refresh.
            shade *= spine * (0.97 + .03 * math.cos((y - 30) / 15))
            pixels[x, y] = tuple(
                round((left[i] * (1 - t) + right[i] * t) * shade)
                for i in range(3)
            )
    return image
