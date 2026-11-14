"""4x4 football timeout pips on the extreme outside edges of the panel.

The three pips share the score's vertical space rather than reserving a
bottom band. Used timeouts retain 20% of the active source RGB value.
"""


def faded_color(hex_color, fraction=0.20):
    color = hex_color.lstrip("#")
    if len(color) != 6:
        raise ValueError("Expected six-digit RGB color")
    return tuple(round(int(color[i:i + 2], 16) * fraction) for i in (0, 2, 4))


def draw_timeouts(draw, home_away, remaining, score, active_color):
    """Draw 3 vertically stacked 4x4 markers; no score-dependent fallback.

    Away uses x=0..3, home uses x=124..127.
    The markers start at y=42 and are separated by one dark pixel row.
    """
    remaining = max(0, min(3, int(remaining)))
    inactive_color = faded_color(active_color)
    left = 0 if home_away == "away" else 124
    for index in range(3):
        top = 42 + 5 * index
        draw.rectangle((left, top, left + 3, top + 3),
                       fill=active_color if index < remaining else inactive_color)
