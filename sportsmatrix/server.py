"""V2-only Flask control plane. No systemctl, GPIO, or V1 access."""
import io
import os
from pathlib import Path
from flask import Flask, jsonify, request, render_template, send_file
import json
import time
from . import __version__
from .configuration import ConfigStore
from .registry import LEAGUES, PROFILES, supported
from .preview import render_fixture

BASE = Path(__file__).resolve().parent.parent

def create_app(config_path=None):
    app = Flask(__name__, template_folder=str(BASE / "sportsmatrix" / "templates"))
    store = ConfigStore(config_path or os.environ.get("SPORTSMATRIX_CONFIG", BASE / "config" / "settings.json"))
    app.config["STORE"] = store
    token = os.environ.get("SPORTSMATRIX_API_TOKEN", "")

    @app.before_request
    def protect_writes():
        if request.method not in ("GET", "HEAD", "OPTIONS"):
            if not token or request.headers.get("Authorization") != "Bearer " + token:
                return jsonify(error="API token required", ok=False), 401

    @app.get("/")
    def home():
        return render_template("control.html")

    @app.get("/api/v1/leagues")
    def leagues():
        return jsonify(leagues=[vars(x) for x in LEAGUES.values()])

    @app.get("/api/v1/status")
    def status():
        state = store.read()
        virtual_state = None
        status_path = BASE / "output" / "virtual_state.json"
        if status_path.exists():
            try:
                candidate = json.loads(status_path.read_text())
                if time.time() - candidate.get("updated_at", 0) < 120:
                    virtual_state = candidate
            except (ValueError, OSError, TypeError): pass
        return jsonify(version=__version__, state=state, virtual_state=virtual_state,
                       available_leagues=list(supported()),
                       profiles={key: {"cols": size[0], "rows": size[1]} for key,size in PROFILES.items()},
                       output="virtual", hardware_active=False,
                       preview_mode="recorded_fixture")

    @app.put("/api/v1/settings")
    def settings():
        data = request.get_json(silent=True)
        if not isinstance(data, dict): return jsonify(ok=False, error="JSON object required"), 400
        if set(data) - {"league", "brightness", "power", "profile", "sport_preferences", "schedule"}:
            return jsonify(ok=False, error="Unknown setting"), 400
        try:
            state = store.update(data)
        except ValueError as exc:
            return jsonify(ok=False, error=str(exc)), 400
        return jsonify(ok=True, state=state)

    @app.get("/api/v1/preview.png")
    def preview():
        state = store.read()
        league = request.args.get("league", state.get("league", "nhl"))
        profile = request.args.get("profile", state.get("profile", "enhanced_128x64"))
        if league not in supported() or profile not in PROFILES:
            return jsonify(ok=False, error="Unsupported league/profile"), 400
        try:
            live_path = BASE / "output" / "virtual_live.png"
            state_path = BASE / "output" / "virtual_state.json"
            if live_path.exists() and state_path.exists():
                try:
                    latest = json.loads(state_path.read_text())
                    if (latest.get("league") == league and latest.get("profile") == profile
                            and time.time()-latest.get("updated_at", 0) < 120):
                        return send_file(live_path, mimetype="image/png", max_age=0)
                except (ValueError, OSError, TypeError): pass
            png = render_fixture(league, profile)
        except (FileNotFoundError, ValueError) as exc:
            return jsonify(ok=False, error=str(exc)), 404
        return send_file(io.BytesIO(png), mimetype="image/png", max_age=0)


    @app.get("/api/v1/teams/<league>")
    def teams(league):
        """Full-name provider directory. Never guess team IDs from abbreviations."""
        paths = {"nfl": "football/nfl", "cfb": "football/college-football", "nhl": "hockey/nhl"}
        if league not in paths:
            return jsonify(teams=[], error="Team directory not available for this league"), 404
        try:
            import requests
            url = "https://site.api.espn.com/apis/site/v2/sports/" + paths[league] + "/teams"
            response = requests.get(url, params={"limit": 500}, timeout=9)
            response.raise_for_status()
            items = response.json().get("sports", [{}])[0].get("leagues", [{}])[0].get("teams", [])
            result = []
            for item in items:
                team = item.get("team", {})
                if str(team.get("id", "")).isdigit():
                    result.append({"id": str(team["id"]), "name": team.get("displayName", ""),
                                   "abbreviation": team.get("abbreviation", ""),
                                   "logo": (team.get("logos") or [{}])[0].get("href", "")})
            return jsonify(teams=sorted(result, key=lambda x: x["name"]))
        except (requests.RequestException, ValueError, IndexError, KeyError) as exc:
            return jsonify(teams=[], error="Team directory temporarily unavailable"), 503

    @app.get("/healthz")
    def health():
        return jsonify(ok=True, version=__version__)
    return app

if __name__ == "__main__":
    create_app().run(host=os.environ.get("SPORTSMATRIX_HOST", "127.0.0.1"),
                     port=int(os.environ.get("SPORTSMATRIX_PORT", "8082")))
