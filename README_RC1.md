# SportsMatrix V2 — software integration RC1

**Status: development release candidate, not hardware-certified or production-ready.**

## Scope

- Preserves existing CFB, NFL, NHL and Golf V2 rendering source and cached logos.
- Adds an extensible league registry. Future leagues (WNBA, NWSL, PWHL, PLL, etc.) are **disabled** until adapters/renderers are written and tested.
- Adds a V2-only Flask API and unified control page. No V1 systemctl calls, GPIO initialization, or hardware writes.
- Stores league, brightness, power preference, hardware profile and per-league favorites atomically in V2 `config/settings.json`.
- Provides recorded image previews at 128×64 and a **provisional** downsampled 64×32 image. This is **not native compact rendering** and must not be marketed as final legacy compatibility.
- Includes test fixtures from the existing project and an isolated web service unit.

## Installation (test on Pi without affecting V1)

1. Extract this archive into `/home/scoreboard/sports/sportsmatrix_v2_rc1` (do **not** overwrite `sportsmatrix_mvp` or your working `sportsmatrix_v2`).
2. Run `bash deployment/install_side_by_side.sh` in the extracted folder. Requires internet for pip packages.
3. Run `set -a; source .env; set +a; .venv/bin/python -m sportsmatrix.server` from the folder.
4. Open `http://scoreboard.local:8082/` on the same trusted LAN. For saving settings, use the generated API token from `.env` when prompted. **Do not publish port 8082 to the internet.**
5. Stop with Ctrl-C. No systemd unit is installed by the script.

The optional `deployment/sportsmatrix-v2-web.service` is a reference unit for a later controlled installation; do not enable it until testing.

## API

- `GET /healthz` — liveness
- `GET /api/v1/leagues` — supported and future league registry
- `GET /api/v1/status` — settings, capabilities, virtual output state
- `GET /api/v1/preview.png?league=nhl&profile=enhanced_128x64` — recorded preview
- `PUT /api/v1/settings` — atomic settings patch; requires `Authorization: Bearer <token>`

Example: `curl -X PUT http://scoreboard.local:8082/api/v1/settings -H 'Content-Type: application/json' -H "Authorization: Bearer $SPORTSMATRIX_API_TOKEN" -d '{"league":"nhl","sport_preferences":{"nhl":{"favorite_team":"SJ","mode":"only","favorite_seconds":90}}}'`

## Important limitations / blockers

1. The new web API **does not yet drive the hardware matrix loop**. It writes validated settings for a later hardware-safe integration.
2. Preview images default to **recorded snapshots**. An optional live virtual worker is included (`.venv/bin/python -m sportsmatrix.worker` in a second terminal). It fetches ESPN and writes `output/virtual_live.png` without using GPIO; the web preview switches to live when matching fresh output is available. This worker has not been tested against live ESPN in this offline build environment.
3. Native 64×32 layouts are not complete; current compact output is provisional scaling.
4. NHL favorite selection in the existing runtime remains separate from the new generic preference policy; other sport rotations have not been migrated.
5. Home Assistant: API contract exists; entity configuration is documented, but no installed custom HA integration or live end-to-end test has been completed.
6. Network-dependent ESPN behavior and hardware operation require testing on the Pi.
7. Flask is required. Offline build environment did not have Flask installed and could not fetch it, so HTTP integration tests were **not executed here**.

## Test command

`.venv/bin/python -m unittest discover -s tests -v`

## Rollback

Stop this V2-only web process. The installation script doesn't modify production services, so no V1 rollback is needed. Restore the working V2 directory independently if subsequently promoting the package.

## Optional virtual worker

With the web server running, start `.venv/bin/python -m sportsmatrix.worker` in a separate terminal in the same directory. It will fetch ESPN data, update a virtual framebuffer and publish its status. Do not run the old `matrix_loop.py` until hardware validation.
