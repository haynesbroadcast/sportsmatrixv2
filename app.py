from nhl_runtime import fetch_events as fetch_nhl_events
from render.nhl_v2 import render as render_nhl, OUTPUT as NHL_OUTPUT
import argparse
import json
from pathlib import Path

from plugins.espn import fetch_games, fetch_golf_leaderboard
from selector import choose_featured_game
from render.preview import render_game, render_test_pattern
from render.golf import render_golf
from cfb_runtime import fetch_events
import shutil
from render.cfb_v2 import API as CFB_API, fetch as cfb_fetch, priority as cfb_priority, render as render_cfb, OUTPUT as CFB_OUTPUT


SETTINGS_PATH = Path("config/settings.json")


def load_settings():
    return json.loads(SETTINGS_PATH.read_text())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--preview", action="store_true")
    parser.add_argument("--test-pattern", action="store_true")
    args = parser.parse_args()

    settings = load_settings()

    if args.test_pattern:
        path = "output/test_pattern.png"
        render_test_pattern(path)
        print(f"Created {path}")
        return

    path = "output/featured_preview.png"
    league = settings.get("league", "worldcup")

    if league == "nhl":
        events = fetch_nhl_events()
        if not events:
            print("No NHL games available.")
            return
        render_nhl(events[0])
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(NHL_OUTPUT, path)
        print(f"Created {path} | NHL")
        return

    if league == "cfb":
        events = fetch_events()
        if not events:
            print("No CFB games available.")
            return
        event = sorted(events, key=cfb_priority)[0]
        render_cfb(event)
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(CFB_OUTPUT, path)
        print(f"Created {path} | CFB")
        return

    if league == "golf":
        board = fetch_golf_leaderboard()
        render_golf(board, settings, path, page=0)
        print(f"Created {path}")
        print(f"{board.get('title', 'GOLF')} | golf")
        return

    games = fetch_games(league)
    game, mode = choose_featured_game(games, settings)

    if not game:
        print("No game found.")
        return

    render_game(game, mode, settings, path)
    print(f"Created {path}")
    print(f"{game.away.abbr} {game.away.score} vs {game.home.abbr} {game.home.score} | {game.detail} | mode={mode}")


if __name__ == "__main__":
    main()
