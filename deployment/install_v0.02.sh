#!/usr/bin/env bash
# V2-only installer; no services are enabled until explicitly requested.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
if [[ "${EUID}" -eq 0 ]]; then echo 'Run as the scoreboard user, not root.' >&2; exit 1; fi
command -v sudo >/dev/null || { echo 'sudo is required' >&2; exit 1; }
sudo apt-get update
sudo apt-get install -y python3-venv python3-dev build-essential cmake git
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
DRIVER="${SPORTSMATRIX_DRIVER_DIR:-$HOME/rpi-rgb-led-matrix}"
if [[ ! -f "$DRIVER/pyproject.toml" ]]; then
  echo "Driver source not found at $DRIVER. Set SPORTSMATRIX_DRIVER_DIR to the tested checkout." >&2
  exit 1
fi
.venv/bin/python -m pip install "$DRIVER"
.venv/bin/python -c 'from rgbmatrix import RGBMatrix, RGBMatrixOptions; print("rgbmatrix import OK")'
.venv/bin/python -m unittest discover -s tests -p test_display.py -v
echo "Full application test suite requires recorded fixture PNGs in output/; not run by installer."
if [[ ! -f .env ]]; then
  TOKEN="$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')"
  printf 'SPORTSMATRIX_API_TOKEN=%s\nSPORTSMATRIX_HOST=0.0.0.0\nSPORTSMATRIX_PORT=8082\n' "$TOKEN" > .env
  chmod 600 .env
fi
printf '\nSoftware and bindings installed. No services changed.\n'
printf 'To install services after reviewing the configuration: bash deployment/enable_services.sh\n'
