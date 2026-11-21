# SportsMatrix V2 v0.17 — NFL panel polish

**Pre-release**, built on the working v0.16 weekend carousel.

## What changed

- Single-game **overflow within a multi-game kickoff window stays a slate**.
  Seven early games appear as 3 + 3 + 1; the final matchup remains a
  standard-size row, centered on the page. Truly standalone TNF/SNF/MNF
  windows retain their larger full-screen treatment.
- Full-screen pregame header is **MONDAY** for Monday, **SNF** for Sunday
  evening, **TNF** for Thursday evening, or the actual day name otherwise.
- Vertical slate labels use the **broadcast hour**: 1:05 PM and 1:25 PM
  both display **SUN 1PM** rather than the easily confused 105P/125P.
- Added a **reusable contrast-aware alpha keyline** for team logos:
  dark artwork against dark gradients gets a light 1px silhouette;
  pale artwork against pale gradients gets a dark one. Clear artwork
  remains unmodified. This is based on logo/background pixels, not a
  Giants-specific exception, and is suitable for other sports renderers.
- Every NFL screen (slate, standalone pregame, live, final) now shows
  **global carousel position pips** at the bottom-left. All seven pages
  share a seven-position marker, rather than resetting per kickoff window.
- Tests cover sparse overflow, 1PM labels, standalone headings, keylines,
  and seven-page position indicators.

## Upgrade from the working v0.16 checkout

SSH into the Raspberry Pi:

```bash
cd "$(systemctl show -p WorkingDirectory --value sportsmatrix-v2-worker)"
git status --short
git fetch origin
git switch feature/v0.17-nfl-layout-polish 2>/dev/null || git switch --track origin/feature/v0.17-nfl-layout-polish
git pull --ff-only origin feature/v0.17-nfl-layout-polish
.venv/bin/python -m unittest discover -s tests -v
sudo systemctl restart sportsmatrix-v2-worker
```

If Git reports conflicts with modified generated images, stop; preserve
those tracked outputs before switching. Do not delete the untracked logo
caches. Do not restart if tests fail.

The usual control-room NFL / All Teams mode will use the new carousel
automatically. A photo of a dark-blue logo such as the Giants is useful
for checking the adaptive silhouette on the physical HUB75 panel.

## Rollback

```bash
git switch feature/v0.16-nfl-weekend-carousel
sudo systemctl restart sportsmatrix-v2-worker
```

No changes to GPIO wiring, RGB matrix services, API tokens or configuration.
