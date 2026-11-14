# Home Assistant — SportsMatrix V2 (v0.12)

SportsMatrix exposes a simple LAN-only Home Assistant REST interface at
`http://sportsmatrix-lab.local:8082`. It is the SAME state as the Control Room:
changing HA controls updates the physical scoreboard and vice versa.

## API

- `GET /api/v1/ha/state` → JSON `{"league":"nhl","brightness":20,"power":"on","available_leagues":["nhl", ...],"version":"0.12"}`
- `POST /api/v1/ha/control` → JSON payload with any subset of:
  - `league`: one of `nhl,nfl,cfb,golf,nba,wnba,nwsl,epl,mls,mlb`
  - `brightness`: integer 1–100
  - `power`: `on`, `off`, or `auto`
- Errors return HTTP 400 with `{"ok":false,"error":"..."}`.
- By default, **no token is required** on the LAN. If `SPORTSMATRIX_REQUIRE_AUTH=1`,
  POST requests require an `Authorization: Bearer <token>` header.

Example:
```bash
curl -X POST http://sportsmatrix-lab.local:8082/api/v1/ha/control \
  -H 'Content-Type: application/json' \
  -d '{"league":"epl","brightness":35,"power":"on"}'
curl http://sportsmatrix-lab.local:8082/api/v1/ha/state
```

## Home Assistant configuration.yaml

The REST sensor polls the live settings. Template entities are intentionally
not assumed; use three `rest_command` services to control the device. This
keeps HA setup portable and works from scripts, automations, and dashboard
buttons without requiring HACS or MQTT.

```yaml
rest:
  - resource: http://sportsmatrix-lab.local:8082/api/v1/ha/state
    scan_interval: 15
    sensor:
      - name: SportsMatrix Sport
        unique_id: sportsmatrix_sport
        value_template: "{{ value_json.league }}"
        json_attributes:
          - brightness
          - power
          - available_leagues
          - version

rest_command:
  sportsmatrix_set_sport:
    url: http://sportsmatrix-lab.local:8082/api/v1/ha/control
    method: POST
    content_type: application/json
    payload: '{"league": "{{ league }}"}'
  sportsmatrix_set_brightness:
    url: http://sportsmatrix-lab.local:8082/api/v1/ha/control
    method: POST
    content_type: application/json
    payload: '{"brightness": {{ brightness | int }}}'
  sportsmatrix_set_power:
    url: http://sportsmatrix-lab.local:8082/api/v1/ha/control
    method: POST
    content_type: application/json
    payload: '{"power": "{{ power }}"}'
```

Restart Home Assistant after editing configuration.yaml.

In Developer Tools → Actions, call `rest_command.sportsmatrix_set_sport`
with `{"league":"golf"}` or `{"league":"epl"}`.
For brightness call `rest_command.sportsmatrix_set_brightness` with
`{"brightness":35}`. To blank the panel use
`rest_command.sportsmatrix_set_power` with `{"power":"off"}`.

If Home Assistant cannot resolve `sportsmatrix-lab.local` via mDNS,
use the Pi's reserved LAN IP address instead.
