# SportsMatrix V2 v0.18 — Cross-sport layout consistency

**Pre-release; based on the approved v0.17 NFL design. NFL visuals and
NFL schedule logic are intentionally unchanged.**

## Where the NFL lessons apply

| League | Pregame | Live/final | Logo treatment | Page position |
| --- | --- | --- | --- | --- |
| NFL | Existing approved 3-up/full-screen | Existing football scoreboard | Existing adaptive keyline | Existing weekend-wide pips |
| CFB | 3-up when games share a kickoff window; one-off feature retains rankings | Existing football scores, possession, down and timeouts | Adaptive alpha keyline | Daily carousel pips |
| NHL | 3-up when multiple games share a window; standalone feature | Existing score, period, shots and power-play | Adaptive alpha keyline | Daily carousel pips |
| NBA/WNBA | 3-up same-window pregame, standalone feature | Existing basketball scores/period | Adaptive alpha keyline | Daily carousel pips |
| MLS/NWSL/EPL | 3-up same-window pregame, standalone feature | Existing soccer score and match clock | Adaptive alpha keyline | Daily carousel pips |
| MLB | Keep score-first R/H/E, bases, outs and challenge dots | Unchanged | No logos by design | No overlay: no safe free pixels |
| Golf | Keep 4-row tournament-themed leaderboard | Unchanged | Not applicable | 2px pips in header divider, never over scores |

**Shared design principles:** native 128×64, alpha-aware logos, contrast
outlines based on actual logo/background pixels, team-color gradients on
pregame screens, readable upright bitmap labels, vertical weekday/time
strip for multi-game slates, overflow retaining slate format, and a
global carousel indicator rather than per-window counters.

## Calendar policy

The NFL has a unique Thursday–Monday viewing week. Other sports do not.
For NHL, CFB, basketball and soccer, the carousel shows **all games on
the current Pacific calendar day**, including scores from today's live
and finished games. If none exist, it shows the **next scheduled game
day**. A live overnight game remains eligible until it ends. Games
within 45 minutes of the window's first kickoff share a 3-up slate;
mixed live/pregame groups are always full-game pages so no live scores
are hidden. The source provider determines which games are available.

A one-game window gets a full-screen pregame feature. When a window
overflows 3+3+1, the last game keeps the slate design. NFL-specific
SNF/TNF/MNF labels are **not** used for other leagues: their standalone
feature headings are the actual weekday.

This is not a redesign of baseball's dense scoreboard or golf's
leaderboard. Both retain their specialized information hierarchy.

## Upgrade from v0.17

On the Pi, first make sure the shell is at a normal prompt and that
you have completed any password prompt from a previous command:

```bash
cd "$(systemctl show -p WorkingDirectory --value sportsmatrix-v2-worker)"
git status --short
git fetch origin
if git show-ref --verify --quiet refs/heads/feature/v0.18-cross-sport-layouts; then
    git switch feature/v0.18-cross-sport-layouts
else
    git switch --track origin/feature/v0.18-cross-sport-layouts
fi
git pull --ff-only origin feature/v0.18-cross-sport-layouts
git branch --show-current
.venv/bin/python -m unittest discover -s tests -v
sudo systemctl restart sportsmatrix-v2-worker
```

Do **not** restart if branch switching or tests fail. Do not run
`git clean` or delete downloaded logo caches. Select NHL, CFB,
NBA, WNBA, MLS, NWSL, EPL or Golf in the existing UI and check the
physical panel.

## Roll back

```bash
git switch feature/v0.17-nfl-layout-polish
sudo systemctl restart sportsmatrix-v2-worker
```

No changes to HAT wiring, service units, ESPN credentials, or API
configuration. The NFL implementation is deliberately left alone.
