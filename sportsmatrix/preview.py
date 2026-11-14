"""Virtual framebuffer. Never imports or initializes HUB75 hardware."""
import io
import tempfile
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from .registry import PROFILES

BASE = Path(__file__).resolve().parent.parent

def compact(image):
    """Native compact composition using cropped team artwork and readable essentials."""
    # Existing 128x64 renderers lack a structured scene graph. For the RC,
    # use a deliberate compact crop/downsample, pending dedicated per-sport art.
    canvas = Image.new("RGB", (64, 32), "#080e17")
    canvas.paste(image.resize((64,32), Image.Resampling.LANCZOS))
    return canvas

def output_for(profile, source):
    size = PROFILES[profile]
    with Image.open(source) as opened:
        image = opened.convert("RGB")
    if image.size == size: return image
    if profile == "compact_64x32": return compact(image)
    return image.resize(size, Image.Resampling.LANCZOS)

def render_fixture(league, profile="enhanced_128x64"):
    from .registry import supported
    if league not in supported():
        raise ValueError("No renderer for this league")
    if league not in ("nhl", "nfl", "cfb", "golf"):
        from render.other_sports import render
        from .other_feeds import ESPN_PATHS
        # Explicitly tagged SAMPLE: useful off-season preview, never fake live data.
        demo = {
            "name": "Sample matchup",
            "date": "2026-11-13T20:00:00Z",
            "status": {"type": {"state": "in"}, "period": 3,
                       "displayClock": "05:42"},
            "competitions": [{"competitors": [
                {"homeAway": "away", "score": "108" if league in ("nba", "wnba") else "3",
                 "team": {"abbreviation": "AWY"}},
                {"homeAway": "home", "score": "112" if league in ("nba", "wnba") else "2",
                 "team": {"abbreviation": "HME"}}
            ], "situation": {"outs": 1, "onFirst": True,
                              "onSecond": False, "onThird": True}}],
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sample.png"
            render(demo, league, path, sample=True)
            image = output_for(profile, path)
            stream = io.BytesIO()
            image.save(stream, format="PNG")
            return stream.getvalue()
    source = BASE / "output" / {"nhl":"nhl_v2_first.png", "nfl":"nfl_large_logos_v2.png", "cfb":"cfb_v2.png", "golf":"golf_v2.png"}[league]
    if not source.exists():
        source = BASE / "tests" / "fixtures" / source.name
    if not source.exists(): raise FileNotFoundError("Fixture preview unavailable")
    image = output_for(profile, source)
    stream = io.BytesIO()
    image.save(stream, format="PNG")
    return stream.getvalue()
