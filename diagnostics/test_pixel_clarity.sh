#!/usr/bin/env bash
# Run from any working directory. Only the physical display service is paused.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SERVICE=sportsmatrix-v2-display.service
[[ -x "$ROOT/.venv/bin/python" ]] || { echo "Run the v0.04 installer first." >&2; exit 1; }
was_active=false
if systemctl is-active --quiet "$SERVICE"; then was_active=true; fi
restore() {
  if [[ "$was_active" == true ]]; then
    echo "Restoring normal SportsMatrix display..."
    sudo systemctl restart "$SERVICE"
  fi
}
trap restore EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
echo "Pausing physical display driver; web and worker continue running..."
sudo systemctl stop "$SERVICE"
echo "Four static patterns, 7 seconds each. Watch the panel and note which blur."
sudo "$ROOT/.venv/bin/python" "$ROOT/diagnostics/pixel_clarity.py"
echo "Pattern test completed."
