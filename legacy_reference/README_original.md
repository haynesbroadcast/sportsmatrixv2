# SportsMatrix MVP

Single featured-game LED scoreboard for Raspberry Pi 64x32 matrix.

## Behavior
- Shows one featured game only.
- Favorite team has priority.
- Holds final score for 15 minutes.
- If another game is later the same day, counts down after final hold.
- If the next game is tomorrow/later, waits until morning before showing countdown.
- No clock mode.
- Web UI is intentionally simple and dark.

## Preview commands

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

python3 app.py --preview
python3 app.py --test-pattern
```

## Web UI

```bash
python3 web/server.py
```

Then open:

```text
http://raspberrypi.local:5000
```

## Notes
Generated placeholder assets are included. Replace files in `assets/logos` or `assets/flags` through the web UI later.
