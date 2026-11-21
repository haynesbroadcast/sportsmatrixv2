# SportsMatrix V2 v0.21 — CFB weekend carousel fix

Fixes the Friday Oregon–Michigan one-page carousel: the CFB renderer
was restricted to today's games even when Saturday ranked games were
available. The worker now uses the already-tested football viewing-week
page builder for CFB, including upcoming days through Monday.

- CFB shows all matchups featuring either Top 25 team, plus every
  postseason/bowl game (v0.19 eligibility unchanged).
- Games are ordered by Pacific-time kickoff day/window, with three-up
  pregame slates and full-screen live/final scores. The carousel's
  global page indicator counts all eligible pages.
- Games from previous calendar days are not replayed.
- NHL, NBA/WNBA, soccer retain their daily focus.
- All v0.20 live/final team-color fades remain unchanged.

## Install on Pi

```bash
cd ~/sports/sportsmatrixv2-v0.06
git fetch origin
if git show-ref --verify --quiet refs/heads/feature/v0.21-cfb-weekend-carousel; then
    git switch feature/v0.21-cfb-weekend-carousel
else
    git switch --track origin/feature/v0.21-cfb-weekend-carousel
fi
git pull --ff-only origin feature/v0.21-cfb-weekend-carousel
git branch --show-current
.venv/bin/python -m unittest discover -s tests -v
```

Only if tests pass:

```bash
sudo systemctl restart sportsmatrix-v2-worker
cat output/virtual_state.json
journalctl -u sportsmatrix-v2-worker -n 12 --no-pager
```

The worker should report `cfb-weekend-X-of-N`. If `N` is still
1, inspect ESPN eligibility/feed results rather than assuming a
carousel problem.

## Rollback

```bash
git switch feature/v0.20-live-game-gradients
sudo systemctl restart sportsmatrix-v2-worker
```
