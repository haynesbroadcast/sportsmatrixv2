#!/usr/bin/env bash
set -euo pipefail
# Run as scoreboard from the extracted release folder; never touches V1 services.
HERE="$(cd "$(dirname "$0")/.." && pwd)"
cd "$HERE"
if [[ ! -f .env ]]; then
  TOKEN="$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')"
  printf 'SPORTSMATRIX_API_TOKEN=%s\nSPORTSMATRIX_HOST=0.0.0.0\nSPORTSMATRIX_PORT=8082\n' "$TOKEN" > .env
  chmod 600 .env
  echo 'Generated .env; keep this token private.'
fi
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m unittest discover -s tests -v
printf '\nStart the V2 control UI with:\n'
printf '  set -a; source .env; set +a; .venv/bin/python -m sportsmatrix.server\n'
printf 'This does not start any LED matrix service.\n'
