# SportsMatrix V2 v0.15 — NFL pregame slate test build

**Pre-release, for on-panel evaluation.** This branch is based on
`fix/v0.14-nfl-windows-cfb-logos`. It does not modify the V1 scoreboard.

## Upgrade the currently active V2 installation

SSH into the Pi as the usual scoreboard user, then:

```bash
cd "$(systemctl show -p WorkingDirectory --value sportsmatrix-v2-worker)"
git status --short
git fetch origin
git switch --track origin/feature/v0.15-nfl-slate-logos
.venv/bin/python -m unittest discover -s tests -v
sudo systemctl restart sportsmatrix-v2-worker
```

**Important:** If `git status --short` shows local changes, do not switch
branches until those changes have been reviewed or saved. No reinstall of
system services, RGBMatrix driver, or Pi configuration is required.

Set NFL to **all teams** in the existing web control interface. With two
or more **upcoming games in the same kickoff window**, the worker now displays
up to three games per native 128x64 page and rotates every 12 seconds.
For a six-game window this produces two pages. A single matchup, live
game, or completed game still uses the existing full-game renderer.

The new renderer downloads team logos from the ESPN team data already used
by the NFL feed, trims transparent margins, fits them within 22x17 pixels,
reduces faint alpha halos, and caches the result in
`assets/nfl/slate-v015/`. This cache is distinct from existing NFL logos.
If a logo cannot load, the three-letter team abbreviation is shown instead.

Preview the latest frame in `output/virtual_live.png`. To check the worker:

```bash
sudo systemctl --no-pager status sportsmatrix-v2-worker
journalctl -u sportsmatrix-v2-worker -n 40 --no-pager
```

## Roll back the code without changing local settings

From the same checkout:

```bash
git switch -
sudo systemctl restart sportsmatrix-v2-worker
```

## Scope and limitations

- This is the **pregame slate only**. The existing live-game layout remains.
- The clock strip is sideways and uses Pacific time.
- No synthetic fixtures are shown on the physical scoreboard; the slate
  depends on actual ESPN schedule data and network availability.
- Native-resolution rendering and unit tests are included, but actual HUB75
  readability and color calibration still require a physical-panel review.
