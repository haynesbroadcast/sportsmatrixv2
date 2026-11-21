"""Reusable, alpha-aware logo compositing for tiny LED sports graphics.

A one-pixel silhouette keyline is added only when the logo and its local
background have insufficient contrast. This is based on pixels, not teams,
so the same treatment can be used for other leagues and color schemes.
"""
from PIL import Image, ImageChops, ImageFilter, ImageStat


def _luminance(rgb):
    return 0.2126 * rgb[0] + 0.7152 * rgb[1] + 0.0722 * rgb[2]


def composite_logo(canvas, logo, x, y, threshold=80):
    """Alpha-composite logo at (x, y), with a contrast-aware 1px outline.

    Modifies an RGBA canvas in place; returns whether artwork was drawn.
    The original transparent pixels and colors are retained.
    """
    if logo is None:
        return False
    logo = logo.convert("RGBA")
    alpha = logo.getchannel("A")
    if not alpha.getbbox():
        return False

    # Measure the actual colored logo against the exact underlying gradient.
    sample = canvas.crop((x, y, x + logo.width, y + logo.height)).convert("RGB")
    bg = _luminance(ImageStat.Stat(sample).mean[:3])
    fg = _luminance(ImageStat.Stat(logo.convert("RGB"), mask=alpha).mean[:3])

    if abs(fg - bg) < threshold:
        # Dark-blue artwork on a dark-blue gradient needs a light silhouette;
        # bright artwork on a pale background needs a dark one.
        keyline = (244, 246, 251) if bg < 128 else (5, 8, 14)
        padded = Image.new("RGBA", (logo.width + 2, logo.height + 2),
                           (0, 0, 0, 0))
        padded.paste(logo, (1, 1))
        mask = padded.getchannel("A")
        border = ImageChops.subtract(mask.filter(ImageFilter.MaxFilter(3)), mask)
        outline = Image.new("RGBA", padded.size, keyline + (0,))
        outline.putalpha(border)
        canvas.alpha_composite(outline, (x - 1, y - 1))

    canvas.alpha_composite(logo, (x, y))
    return True
