# SportsMatrix V2

A sports scoreboard for the Raspberry Pi and HUB75 LED matrices, including a web control page and live sports feeds.

**Current development version: v0.04 (pre-release).** The Pi 4 + Adafruit HAT + 128×64 HUB75 configuration is under active validation. Do not treat this as a production-certified installer.

**Start here:** [v0.04 installation and upgrade instructions](INSTALL_v0.04.md).

Intended workflow: flash Raspberry Pi OS → clone this repository → run `deployment/install.sh` → configure local API credentials and settings → connect the matrix → activate the three V2 services → verify automatic startup.

Configuration and API credentials are local machine files, not committed to Git. The existing v0.03 installation can be kept side by side for rollback.
