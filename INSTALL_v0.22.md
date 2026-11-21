# SportsMatrix V2 v0.22 — Accurate "On the Board" mirror

The Control Room's "On the Board" card no longer falls back to a
recorded NHL/NFL/CFB fixture while a different sport is selected.

- The card reads the **actual worker framebuffer** at
  `/api/v1/board.png`, which is the same 128×64 PNG consumed by the
  physical display service.
- The server serves that frame **only** if the worker state is fresh,
  the active league/profile match the configured display, the hardware
  service reports `frame_active`, and power/schedule allow display.
- The browser refreshes every 5 seconds, following game rotation.
  Changing the selected sport tile does **not** pretend the panel
  switched before "Apply Display" is pressed.
- If no valid live physical frame exists, the card says
  "No active scoreboard frame" rather than showing a sample.
- The header/API version now reports v0.22 instead of v0.13.
- The older `/api/v1/preview.png` fixture endpoint remains for
  explicit testing, but is **not** used by "On the Board."
- v0.21 CFB weekend carousel, v0.20 live gradients, and v0.19
  Top 25-or-bowl filter remain unchanged.

## Pi upgrade

```bash
cd ~/sports/sportsmatrixv2-v0.06
git fetch origin
if git show-ref --verify --quiet refs/heads/feature/v0.22-live-board-mirror; then
    git switch feature/v0.22-live-board-mirror
else
    git switch --track origin/feature/v0.22-live-board-mirror
fi
git pull --ff-only origin feature/v0.22-live-board-mirror
git branch --show-current
.venv/bin/python -m unittest discover -s tests -v
```

If tests pass, restart **the API service** to load the updated Flask
routes and template. The worker and display do not need to restart:

```bash
sudo systemctl restart sportsmatrix-v2-api
systemctl is-active sportsmatrix-v2-api
```

Reload Control Room in the browser (hard refresh if an old template
is cached). Verify the card shows the active CFB game and follows
rotation. The panel must show an unavailable message if the worker
or hardware is inactive.

## Rollback

```bash
git switch feature/v0.21-cfb-weekend-carousel
sudo systemctl restart sportsmatrix-v2-api
```
