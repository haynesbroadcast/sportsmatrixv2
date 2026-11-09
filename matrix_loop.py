from nhl_runtime import NHLRotation
from render.nhl_v2 import render as render_nhl, OUTPUT as NHL_OUTPUT
from render.nfl_v2 import render as render_nfl, OUTPUT as NFL_OUTPUT
from nfl_runtime import NFLRotation
import json
import time
import shutil
from pathlib import Path

from PIL import Image
from rgbmatrix import RGBMatrix, RGBMatrixOptions

from plugins.espn import fetch_games, fetch_golf_leaderboard
from selector import choose_featured_game
from render.preview import render_game
from render.golf import render_golf
from golf_runtime import GolfRotation
from cfb_runtime import CFBRotation
from render.cfb_v2 import API as CFB_API, fetch as cfb_fetch, priority as cfb_priority, render as render_cfb, OUTPUT as CFB_OUTPUT


SETTINGS_PATH = Path("config/settings.json")
IMAGE_PATH = Path("output/featured_preview.png")


def load_settings():
    return json.loads(SETTINGS_PATH.read_text())


def make_matrix(settings):
    display = settings.get("display", {})

    options = RGBMatrixOptions()
    options.rows = int(display.get("rows", 32))
    options.cols = int(display.get("cols", 64))
    options.chain_length = 1
    options.parallel = 1
    options.hardware_mapping = display.get("gpio_mapping", "adafruit-hat")
    options.gpio_slowdown = int(display.get("slowdown_gpio", 2))
    options.brightness = int(settings.get("brightness", display.get("brightness", 100)))
    options.disable_hardware_pulsing = True
    options.drop_privileges = False

    return RGBMatrix(options=options)


def render_once(matrix):
    settings = load_settings()
    league = settings.get("league", "worldcup")

    games = fetch_games(league)
    game, mode = choose_featured_game(games, settings)

    if not game:
        print("No game found.")
        return

    render_game(game, mode, settings, IMAGE_PATH)

    image = Image.open(IMAGE_PATH).convert("RGB").resize((
                    int(settings.get("display", {}).get("cols", 128)),
                    int(settings.get("display", {}).get("rows", 64))
                ))
    matrix.SetImage(image)

    print(
        f"{game.away.abbr} {game.away.score} vs "
        f"{game.home.abbr} {game.home.score} | "
        f"{game.detail} | mode={mode}"
    )


def main():
    settings = load_settings()
    matrix = make_matrix(settings)
    default_refresh = int(settings.get("refresh_seconds", 60))
    cfb_rotation = CFBRotation()
    nfl_rotation = NFLRotation()
    nhl_rotation = NHLRotation()
    golf_rotation = GolfRotation()
    print(f"SportsMatrix loop started. Default refresh: {default_refresh}s")

    while True:
        sleep_for = default_refresh

        try:
            settings = load_settings()
            league = settings.get("league", "worldcup")

            if league == "nhl":
                event = nhl_rotation.tick()
                if event:
                    render_nhl(event)
                    shutil.copyfile(NHL_OUTPUT, IMAGE_PATH)
                    display = settings.get("display", {})
                    size = (
                        int(display.get("cols", 128)),
                        int(display.get("rows", 64))
                    )
                    with Image.open(IMAGE_PATH) as source:
                        image = source.convert("RGB")
                    if image.size != size:
                        image = image.resize(size)
                    matrix.SetImage(image)
                    print("NHL:", event["name"])
                else:
                    print("NHL: No relevant games available.")
                sleep_for = 5

            elif league == "nfl":
                event = nfl_rotation.tick()
                if event:
                    render_nfl(event)
                    shutil.copyfile(NFL_OUTPUT, IMAGE_PATH)
                    display = settings.get("display", {})
                    size = (
                        int(display.get("cols", 128)),
                        int(display.get("rows", 64))
                    )
                    with Image.open(IMAGE_PATH) as source:
                        image = source.convert("RGB")
                    if image.size != size:
                        image = image.resize(size)
                    matrix.SetImage(image)
                    print("NFL:", event["name"])
                else:
                    print("NFL: No relevant games available.")

                sleep_for = 5

            elif league == "cfb":
                event = cfb_rotation.tick()
                if event:
                    render_cfb(event)
                    shutil.copyfile(CFB_OUTPUT, IMAGE_PATH)
                    display = settings.get("display", {})
                    size = (
                        int(display.get("cols", 128)),
                        int(display.get("rows", 64))
                    )
                    with Image.open(IMAGE_PATH) as source:
                        image = source.convert("RGB")
                    if image.size != size:
                        image = image.resize(size)
                    matrix.SetImage(image)
                    print("CFB:", event["name"])
                else:
                    print("CFB: No relevant games available.")

                sleep_for = 5

            elif league == "golf":
                board, page = golf_rotation.tick()
                if board:
                    render_golf(board, settings, IMAGE_PATH, page=page)
                    display = settings.get("display", {})
                    size = (
                        int(display.get("cols", 128)),
                        int(display.get("rows", 64))
                    )
                    with Image.open(IMAGE_PATH) as source_image:
                        image = source_image.convert("RGB")
                    if image.size != size:
                        image = image.resize(size)
                    matrix.SetImage(image)
                    print("Golf:", board.get("title"), "page", page + 1)
                sleep_for = 5
            else:
                games = fetch_games(league)
                game, mode = choose_featured_game(games, settings)

                if not game:
                    print("No game found.")
                else:
                    render_game(game, mode, settings, IMAGE_PATH)
                    image = Image.open(IMAGE_PATH).convert("RGB").resize((
                    int(settings.get("display", {}).get("cols", 128)),
                    int(settings.get("display", {}).get("rows", 64))
                ))
                    matrix.SetImage(image)

                    print(
                        f"{game.away.abbr} {game.away.score} vs "
                        f"{game.home.abbr} {game.home.score} | "
                        f"{game.detail} | mode={mode}"
                    )

                    if game.status == "in":
                        sleep_for = 15
                    elif mode == "countdown":
                        sleep_for = 30
                    elif mode == "next_day_wait":
                        sleep_for = 300

        except Exception as e:
            print(f"ERROR: {e}")

        print(f"Next refresh in {sleep_for}s")
        time.sleep(sleep_for)


if __name__ == "__main__":
    main()
