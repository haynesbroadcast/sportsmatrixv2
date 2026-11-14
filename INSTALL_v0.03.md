# SportsMatrix V2 v0.03 — Pi 4 / 128×64 deployment

This is a pre-release deployment candidate, not a verified shippable release. It leaves V1 untouched. Do not run the old `matrix_loop.py` simultaneously with the new display service.

## Side-by-side installation (recommended)

Copy this archive to the Pi, extract it under `~/sports/` so it creates `~/sports/sportsmatrixv2/` **only if you have backed up the existing directory**. Safer: extract into a staging directory and rename the extracted `sportsmatrixv2` folder to `sportsmatrixv2-v0.03` before running its installer.

From the new folder:

```sh
bash deployment/install.sh --start
```

The installer migrates settings from `~/sports/sportsmatrixv2/config/settings.json` if installing into a different directory, installs dependencies and Python bindings, and tests the app. It uses the existing `~/rpi-rgb-led-matrix` checkout without changing it; if absent, it clones and checks out the previously tested `b4dc553` commit. It does not change the Pi's boot config or HAT solder jumper. The services are enabled only when `--start` is supplied.

**Potential port conflict:** web defaults to port 8082. Stop any old V2 web instance first if already using that port. No V1 service is intentionally stopped.

Check:

```sh
sudo systemctl status sportsmatrix-v2-web sportsmatrix-v2-worker sportsmatrix-v2-display
curl -fsS http://localhost:8082/healthz
```

Control UI: `http://sportsmatrix-lab.local:8082/`. Token is stored in `.env` (do not share it).

Stop or roll back V2 only:

```sh
sudo systemctl disable --now sportsmatrix-v2-web sportsmatrix-v2-worker sportsmatrix-v2-display
```

## Known limitations

- Hardware output validated previously with a single NHL image and the Adafruit HAT; this release's unattended boot and live feed behavior still require Pi validation.
- The physical display supports only `enhanced_128x64`. The web interface also exposes a compact profile for virtual previews; selecting it will intentionally blank the 128×64 panel.
- Live ESPN data availability depends on provider responses. No fixture is substituted for missing live data.
- No system-wide V1 or existing driver installation is modified.
