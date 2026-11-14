#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
USER_NAME="$(id -un)"
if [[ "$EUID" -eq 0 ]]; then echo 'Run as the deployment user.' >&2; exit 1; fi
[[ -f "$ROOT/.env" && -x "$ROOT/.venv/bin/python" ]] || { echo 'Run bash deployment/install.sh first' >&2; exit 1; }
for name in web worker display; do
  case "$name" in
    web) COMMAND='-m sportsmatrix.server';;
    worker) COMMAND='-m sportsmatrix.worker';;
    display) COMMAND='-m sportsmatrix.display';;
  esac
  unit="$(mktemp)"
  cat > "$unit" <<EOF
[Unit]
Description=SportsMatrix V2 $name
After=network-online.target
Wants=network-online.target
[Service]
Type=simple
User=$USER_NAME
WorkingDirectory=$ROOT
EnvironmentFile=$ROOT/.env
ExecStart=$ROOT/.venv/bin/python $COMMAND
Restart=on-failure
RestartSec=5
[Install]
WantedBy=multi-user.target
EOF
  if [[ "$name" == display ]]; then sed -i 's/^User=.*/User=root/' "$unit"; fi
  sudo install -m 0644 "$unit" "/etc/systemd/system/sportsmatrix-v2-$name.service"
  rm -f "$unit"
done
sudo systemctl daemon-reload
if [[ "${1:-}" == '--start' ]]; then
  sudo systemctl enable --now sportsmatrix-v2-web.service sportsmatrix-v2-worker.service sportsmatrix-v2-display.service
  sudo systemctl --no-pager status sportsmatrix-v2-web.service sportsmatrix-v2-worker.service sportsmatrix-v2-display.service || true
else
  echo 'Service units installed, not started. Run: bash deployment/enable_services.sh --start'
fi
