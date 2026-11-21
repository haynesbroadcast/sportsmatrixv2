# SportsMatrix V2 v0.20 — Live game color fades

Extends the approved NFL pregame look to **live and final** score-first
screens. This branch includes v0.19's simple CFB rule (Top 25 team on
either side, or any bowl/postseason game).

## Visual behavior

- **NFL / CFB / NHL / NBA / WNBA / MLS / NWSL / EPL:** Use a subtle,
  continuous away-to-home team-color fade behind live scores, logos,
  clocks and game situation. Final screens use a quieter variation.
- Use the same ESPN team colors and fallback palette as the approved
  pregame artwork. The fade stays darker beneath score numerals and
  through the center column so time, period, down/distance, shots and
  match clock remain legible.
- Retain the exact score-first placement, football timeout indicators,
  possession arrows, CFB rankings, NHL shots/power-play labels, and
  soccer match clock. Logos retain the adaptive contrast keyline.
- **Pregame:** Existing approved three-game slate and standalone
  feature layouts are unchanged.
- **MLB:** Keep the custom R/H/E, base/out and team-row color layout;
  a whole-screen fade would obscure its information hierarchy.
- **Golf:** Keep the tournament-specific leaderboard and score colors.
- All drawing remains native 128x64. No animation, extra feed requests,
  changes to score semantics, or configuration migration.

## Pi upgrade

```bash
cd ~/sports/sportsmatrixv2-v0.06
git fetch origin
if git show-ref --verify --quiet refs/heads/feature/v0.20-live-game-gradients; then
    git switch feature/v0.20-live-game-gradients
else
    git switch --track origin/feature/v0.20-live-game-gradients
fi
git pull --ff-only origin feature/v0.20-live-game-gradients
git branch --show-current
.venv/bin/python -m unittest discover -s tests -v
sudo systemctl restart sportsmatrix-v2-worker
```

Run the restart **only after** the branch and tests are correct.
Avoid deleting logo caches or generated preview images.

## Roll back

```bash
git switch feature/v0.19-cfb-ranked-only
sudo systemctl restart sportsmatrix-v2-worker
```
