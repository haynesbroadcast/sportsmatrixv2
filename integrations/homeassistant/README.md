# Home Assistant integration contract (prototype)

The V2 API can be queried from Home Assistant using a REST sensor. This is **not yet** a fully installed HA custom component. Write actions use a bearer token and the `PUT /api/v1/settings` endpoint. Store the token in Home Assistant `secrets.yaml`, not in publicly shared configuration. The V2 API should remain restricted to a trusted LAN.

Example read-only REST sensor configuration (adapt hostname to your network):

```yaml
rest:
  - resource: http://scoreboard.local:8082/api/v1/status
    scan_interval: 30
    sensor:
      - name: SportsMatrix V2 League
        value_template: "{{ value_json.state.league }}"
      - name: SportsMatrix V2 Brightness
        value_template: "{{ value_json.state.brightness }}"
      - name: SportsMatrix V2 Output
        value_template: "{{ value_json.output }}"
```

Next: HA select/light/switch entities and validated control actions using the same API. Power and brightness are preferences only in this virtual RC; do not label them as physical controls yet.
