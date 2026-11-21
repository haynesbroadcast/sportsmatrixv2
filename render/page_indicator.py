"""Tiny global carousel-position marker for native-resolution sports pages."""
from PIL import ImageDraw


def draw_page_indicator(image, index, total):
    """Draw position among ALL pages, independent of individual game windows.

    Uses a narrow black footer and 2px pips; works on RGB or RGBA images.
    The layout stays within a 128x64 panel and supports up to 40 pages.
    """
    if total is None or total < 2:
        return image
    total = min(int(total), 40)
    index = max(0, min(int(index), total - 1))
    step = min(4, max(3, (image.width - 4) // total))
    end = min(image.width - 1, 3 + (total - 1) * step + 2)
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, image.height - 3, end, image.height - 1),
                   fill=(3, 7, 14))
    for i in range(total):
        x = 2 + i * step
        draw.rectangle((x, image.height - 2, x + 1, image.height - 1),
                       fill=(245, 245, 245) if i == index else (65, 77, 94))
    return image
