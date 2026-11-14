"""Compact football timeout indicators sharing the score's vertical space.

There is deliberately NO bottom timeout row or reserved bottom padding.
Each indicator is an exact 4x4 group of source pixels. Used indicators
remain at 20% of the active color (before the global panel brightness).
"""


def faded_color(hex_color, fraction=0.20):
    color = hex_color.lstrip("#")
    if len(color) != 6:
        raise ValueError("Expected six-digit RGB color")
    return tuple(round(int(color[i:i+2], 16) * fraction) for i in (0, 2, 4))


def draw_timeouts(draw, home_away, remaining, score, active_color):
    """Position timeout pips outside each team's score area.

    One- and two-digit scores: horizontal pips along the outside edge.
    Three-digit scores: vertical stack at the extreme outer edge, avoiding
    the extra width needed by a three-digit numeral. No dedicated row.
    """
    remaining = max(0, min(3, int(remaining)))
    inactive_color = faded_color(active_color)
    if len(str(score)) >= 3:
        boxes = [(0 if home_away == "away" else 124, 38 + i * 5) for i in range(3)]
    else:
        xs = (0, 5, 10) if home_away == "away" else (114, 119, 124)
        boxes = [(xs[i], 47) for i in range(3)]
    for index, (left, top) in enumerate(boxes):
        draw.rectangle((left, top, left + 3, top + 3),
                       fill=active_color if index < remaining else inactive_color)
