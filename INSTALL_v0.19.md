# SportsMatrix V2 v0.19 — Simple CFB filter

The CFB carousel includes **only**:

1. Games where at least one team is ranked #1–25 in the ESPN feed.
2. All FBS postseason games (bowl season and College Football Playoff),
   regardless of either team's ranking.

No rivalry exceptions, no conference-championship exceptions during
the regular season, no upset-prediction scoring, and no subjective
importance ranking. ESPN season type 3 identifies the postseason.
Games without reliable rankings or postseason classification are
excluded. No arbitrary ten-game cap.

The v0.18 cross-sport layouts and v0.17 NFL visuals remain unchanged.

## Pi upgrade

```bash
cd ~/sports/sportsmatrixv2-v0.06
git fetch origin
if git show-ref --verify --quiet refs/heads/feature/v0.19-cfb-ranked-only; then
    git switch feature/v0.19-cfb-ranked-only
else
    git switch --track origin/feature/v0.19-cfb-ranked-only
fi
git pull --ff-only origin feature/v0.19-cfb-ranked-only
git branch --show-current
.venv/bin/python -m unittest discover -s tests -v
sudo systemctl restart sportsmatrix-v2-worker
```

Only restart if Git and tests succeed. If switching branches fails
because generated images have changed, preserve them rather than
deleting logo caches.

## Rollback

```bash
git switch feature/v0.18-cross-sport-layouts
sudo systemctl restart sportsmatrix-v2-worker
```
