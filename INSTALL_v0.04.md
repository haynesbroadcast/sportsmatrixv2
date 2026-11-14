# SportsMatrix V2 v0.04 — installation preview

**Pre-release:** this is a deployable test candidate for the Raspberry Pi 4 + Adafruit RGB Matrix + RTC HAT + 128×64 HUB75 panel. It is **not yet validated from a factory-fresh Pi image**. GitHub Actions tests exercise Python code but cannot certify GPIO, panel scanning, power, or first-boot behavior.

## Intended fresh-Pi flow

1. Flash Raspberry Pi OS and enable SSH/network access. Log in as your normal non-root user.
2. Install Git if missing: `sudo apt-get update && sudo apt-get install -y git`
3. Clone the repository into the user's `~/sports` directory (do **not** use `sudo git clone`):

   ```sh
   mkdir -p ~/sports
   git clone --branch release/v0.04-install-preview https://github.com/haynesbroadcast/sportsmatrixv2.git ~/sports/sportsmatrixv2-v0.04
   cd ~/sports/sportsmatrixv2-v0.04
   bash deployment/install.sh
   ```

4. The installer installs Python dependencies, the RGBMatrix Python binding, and the tested driver checkout if not already present; generates a private `.env` API token; creates `config/settings.json`; and runs unit tests. **It does not start services unless given `--start`.**
5. Confirm your HAT jumper, power, panel wiring, and panel hardware match the tested setup. The current physical output configuration is Pi 4, Adafruit HAT, 128×64, BGR color order, GPIO slowdown 4. The installer does not change `/boot/firmware/config.txt` or solder jumpers.
6. Start the three V2 services:

   ```sh
   bash deployment/enable_services.sh --start
   ```

7. Visit `http://<pi-hostname>.local:8082/`. Your API credential is in `~/sports/sportsmatrixv2-v0.04/.env`. **Never paste the token into public chats or push `.env` to GitHub.** Use the control page to select a sport, brightness and power.

## Upgrade from the currently working v0.03 Pi

**Do not overwrite or delete `~/sports/sportsmatrixv2-v0.03`.** Perform the clone and install steps above in `~/sports/sportsmatrixv2-v0.04`, then start services only when ready to switch. The installer defaults to copying settings from the old v0.03 installation, preserving the original; override the source with `SPORTSMATRIX_PREVIOUS_DIR=/path/to/old` if needed. The API token is newly generated for the new directory.

Installing without `--start` leaves the existing v0.03 services running. Running `bash deployment/enable_services.sh --start` re-points all three V2 systemd units to the new directory and **restarts** them. This intentionally switches the active display/web/worker to v0.04, and may briefly blank the panel.

Check after switching:

```sh
sudo systemctl --no-pager status sportsmatrix-v2-web sportsmatrix-v2-worker sportsmatrix-v2-display
curl -fsS http://localhost:8082/healthz
```

Rollback to v0.03 without deleting v0.04:

```sh
cd ~/sports/sportsmatrixv2-v0.03
bash deployment/enable_services.sh --start
```

## What changed in v0.04

- CFB, NFL, and NHL render frames now use `#000000` for background (all LEDs off in the RGB source). This does not cure hardware ghosting or change golf's intentional themed background.
- The installer supports side-by-side upgrade from `sportsmatrixv2-v0.03`, validates its arguments, and keeps credentials local.
- The service installer restarts already-running services so new source is actually loaded.
- Local `config/settings.json` is no longer tracked; `config/settings.example.json` documents the sample structure.
- A background-pixel regression test and GitHub Actions checks were added.

## Remaining validation

Confirm actual black pixels, text clarity, and logo sizing on the physical panel. Pixel text and logos have **not** been changed in this release; that needs comparison on the hardware. Also validate a fresh Pi install, reboot/autostart, credentials, and the return path to v0.03 before calling the installer shippable.
