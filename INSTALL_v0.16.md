# SportsMatrix V2 v0.16 — NFL weekend carousel

**Pre-release, intended for real 128×64 HUB75 panel testing.**
This branch extends v0.15; it does not alter the V1 scoreboard.

## What's different

- Rotate **all remaining NFL games from the current Pacific calendar day
  through Monday**, chronologically, not just the next kickoff window.
  Tuesday starts the next viewing week. Friday no longer shows Thursday.
- Keep unusual Thursday/Friday/Saturday holiday matchups, Sunday's early and
  late windows, Sunday night and Monday night when ESPN schedules them.
- Group kickoffs within 45 minutes on the same day. Show up to **three
  upcoming games per 128×64 slate page**; overflow rotates to extra pages.
- One-game windows and lone overflow games use a **full-screen gradient
  feature graphic** with larger team logos, matchup and kickoff details.
- Live and final games keep the existing score-and-situation full-game layout.
- The left strip reads **SUN 10AM**, **THU 5PM**, etc., instead of PT.
  Non-hour kickoffs use a compact label such as **SUN 125P** for 1:25 PM.
- Remove solid black rectangles behind team abbreviations. Tiny dark
  glyph shadows retain legibility without breaking the gradients.

## Upgrade the running v0.15 checkout

SSH into the Pi as your normal user:

```bash
cd "$(systemctl show -p WorkingDirectory --value sportsmatrix-v2-worker)"
git status --short
git fetch origin
git switch --track origin/feature/v0.16-nfl-weekend-carousel
.venv/bin/python -m unittest discover -s tests -v
sudo systemctl restart sportsmatrix-v2-worker
```

If the branch switch is blocked by locally generated images, preserve
only those modified tracked outputs, then retry:

```bash
git stash push -m "Keep local generated frames before v0.16" -- output/cfb_v2.png output/golf_v2.png
git switch --track origin/feature/v0.16-nfl-weekend-carousel
```

Do not run `git clean` or delete the untracked team-logo caches.
The installer, services, API token and display wiring are unchanged.
Select NFL / All Teams in the existing control room.

## Roll back

```bash
git switch -
sudo systemctl restart sportsmatrix-v2-worker
```

## Notes

The carousel uses the live ESPN schedule; no fake games are shown on
the physical scoreboard. If there are no games left before the current
Monday ends, the worker has no remaining weekend page to select.
Team artwork is still cached locally. All rendering is native 128×64.
Automated tests cover holiday scheduling, past-day removal, slate overflow,
single-game feature output and page rotation; real panel readability
requires a photograph after installation.
