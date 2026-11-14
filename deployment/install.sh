#!/usr/bin/env bash
# SportsMatrix v0.09 installation: isolated V2 deployment, no changes to V1.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
case "${1:-}" in
  --start|"") ;;
  --help|-h)
    printf 'Usage: bash deployment/install.sh [--start]\n'
    printf 'Without --start, installs and tests but does not activate services.\n'
    exit 0 ;;
  *) echo "Unknown option: $1 (expected --start or --help)" >&2; exit 2 ;;
esac
if [[ "$EUID" -eq 0 ]]; then echo 'Run as the scoreboard user, not sudo/root.' >&2; exit 1; fi
command -v sudo >/dev/null || { echo 'sudo is required' >&2; exit 1; }
command -v git >/dev/null || { echo 'git is required' >&2; exit 1; }
echo 'Installing SportsMatrix v0.09 prerequisites...'
sudo apt-get update
sudo apt-get install -y python3-venv python3-dev build-essential cmake git pkg-config fonts-liberation fonts-dejavu-core
if [[ ! -x .venv/bin/python ]]; then python3 -m venv .venv; fi
.venv/bin/python -m pip install -r requirements.txt
DRIVER="${SPORTSMATRIX_DRIVER_DIR:-$HOME/rpi-rgb-led-matrix}"
if [[ ! -f "$DRIVER/pyproject.toml" ]]; then
  echo "Driver missing: cloning tested driver commit into $DRIVER"
  git clone https://github.com/hzeller/rpi-rgb-led-matrix.git "$DRIVER"
  git -C "$DRIVER" checkout b4dc553
else
  echo "Using existing driver checkout: $DRIVER (will not modify it)."
fi
.venv/bin/python -m pip install "$DRIVER"
.venv/bin/python -c 'from rgbmatrix import RGBMatrix, RGBMatrixOptions; print("RGB matrix binding OK")'
# Migrate existing settings only when installing side by side; never overwrite local config.
OLD="${SPORTSMATRIX_PREVIOUS_DIR:-$HOME/sports/sportsmatrixv2-v0.03}"
if [[ ! -f "$OLD/config/settings.json" && -f "$HOME/sports/sportsmatrixv2/config/settings.json" ]]; then
  OLD="$HOME/sports/sportsmatrixv2"
fi
if [[ "$OLD" != "$ROOT" && -f "$OLD/config/settings.json" && ! -f config/.migrated ]]; then
  mkdir -p config
  if [[ -f config/settings.json ]]; then cp config/settings.json config/settings.package-default.json; fi
  cp "$OLD/config/settings.json" config/settings.json
  touch config/.migrated
  echo "Copied existing settings from $OLD"
fi
.venv/bin/python - <<'PY'
import json
from pathlib import Path
p=Path('config/settings.json')
s=json.loads(p.read_text()) if p.exists() else {}
s.setdefault('profile', 'enhanced_128x64')
s.setdefault('power', s.get('display_schedule',{}).get('override','on') if s.get('display_schedule',{}).get('override') in ('on','off','auto') else 'on')
old=s.get('display_schedule',{})
s.setdefault('schedule', {'enabled':bool(old.get('enabled',False)), 'on':old.get('on_time','08:00'), 'off':old.get('off_time','22:00')})
s.setdefault('brightness', 20)
s.setdefault('league','nhl')
s.setdefault('sport_preferences',{})
p.parent.mkdir(parents=True, exist_ok=True)
p.write_text(json.dumps(s,indent=2)+'\n')
PY
mkdir -p output
.venv/bin/python -m unittest discover -s tests -v
if [[ ! -f .env ]]; then
  TOKEN="$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')"
  printf 'SPORTSMATRIX_API_TOKEN=%s\nSPORTSMATRIX_HOST=0.0.0.0\nSPORTSMATRIX_PORT=8082\n' "$TOKEN" > .env
  chmod 600 .env
fi
# Credentials stay local; never print tokens to the terminal or commit .env.
chmod 600 .env
printf '\nInstalled and tests passed. Services have NOT been enabled.\n'
if [[ "${1:-}" == '--start' ]]; then
  bash deployment/enable_services.sh --start
else
  printf 'To install and start V2 services: bash deployment/enable_services.sh --start\n'
fi
