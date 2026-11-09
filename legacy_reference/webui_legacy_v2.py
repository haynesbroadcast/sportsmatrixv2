import json
import subprocess
from pathlib import Path

from flask import Flask, render_template, request, redirect, url_for, send_file, jsonify

def development_command(*args, **kwargs):
    # V2 development must never control V1's services.
    return subprocess.CompletedProcess(
        args=args[0] if args else [],
        returncode=1,
        stdout="",
        stderr="V2 development mode"
    )

app = Flask(__name__)

SETTINGS_PATH = Path("config/settings.json")
PREVIEW_PATH = Path("output/featured_preview.png")

SPORTS = {
    "nhl": {"name": "NHL", "short": "NHL", "type": "native"},
    "cfb": {
        "name": "College Football",
        "short": "CFB",
        "type": "native",
    },
    "worldcup": {
        "name": "World Cup",
        "short": "WC",
        "type": "native",
    },
    "golf": {
        "name": "Golf",
        "short": "PGA",
        "type": "native",
    },
    "mlb": {
        "name": "MLB",
        "short": "MLB",
        "type": "external",
    },
    "nfl": {
        "name": "NFL",
        "short": "NFL",
        "type": "native",
    },
}


def load_settings():
    return json.loads(SETTINGS_PATH.read_text())


def save_settings(settings):
    SETTINGS_PATH.write_text(json.dumps(settings, indent=2))


def service_for_league(league):
    if league == "mlb":
        return "mlb-scoreboard"
    if league == "nfl":
        return "nfl-scoreboard"
    return "sportsmatrix"


def service_status(league):
    service = service_for_league(league)

    result = development_command(
        ["systemctl", "is-active", service],
        capture_output=True,
        text=True
    )

    return result.stdout.strip() or "unknown"


def run_switch(sport):
    development_command([
        "/home/scoreboard/sports/sportsmatrix_mvp/.venv/bin/python",
        "/home/scoreboard/sports/sportsmatrix_mvp/switch_sport.py",
        sport
    ])


@app.route("/", methods=["GET", "POST"])
def index():
    settings = load_settings()

    if request.method == "POST":
        sport = request.form.get(
            "sport",
            settings.get("league", "worldcup")
        )

        brightness = int(
            request.form.get(
                "brightness",
                settings.get("brightness", 48)
            )
        )

        settings["league"] = sport
        settings["brightness"] = brightness

        schedule = settings.setdefault("display_schedule", {})
        schedule["enabled"] = request.form.get("schedule_enabled") == "on"
        schedule["on_time"] = request.form.get(
            "on_time",
            schedule.get("on_time", "07:00")
        )
        schedule["off_time"] = request.form.get(
            "off_time",
            schedule.get("off_time", "23:00")
        )

        save_settings(settings)
        run_switch(sport)

        return redirect(url_for("index"))

    league = settings.get("league", "worldcup")

    return render_template(
        "index.html",
        settings=settings,
        sports=SPORTS,
        status=service_status(league),
        current_league=league,
        current_sport=SPORTS.get(league, SPORTS["worldcup"]),
        current_service=service_for_league(league),
    )



@app.route("/lab")
def lab():
    settings = load_settings()
    league = settings.get("league", "worldcup")

    return render_template(
        "lab.html",
        settings=settings,
        sports=SPORTS,
        status=service_status(league),
        current_league=league,
        current_sport=SPORTS.get(league, SPORTS["worldcup"]),
        current_service=service_for_league(league),
    )


@app.route("/scope", methods=["GET", "POST"])
def scope():
    settings = load_settings()

    if request.method == "POST":
        sport = request.form.get(
            "sport",
            settings.get("league", "worldcup")
        )

        brightness = int(
            request.form.get(
                "brightness",
                settings.get("brightness", 48)
            )
        )

        settings["league"] = sport
        settings["brightness"] = brightness
        save_settings(settings)
        run_switch(sport)

        return redirect(url_for("scope"))

    league = settings.get("league", "worldcup")

    return render_template(
        "scope.html",
        settings=settings,
        sports=SPORTS,
        status=service_status(league),
        current_league=league,
        current_sport=SPORTS.get(league, SPORTS["worldcup"]),
        current_service=service_for_league(league),
    )



def all_display_services():
    return ["sportsmatrix", "mlb-scoreboard", "nfl-scoreboard"]


def stop_all_displays():
    for service in all_display_services():
        development_command(["sudo", "systemctl", "stop", service])


def display_running():
    return any(
        development_command(
            ["systemctl", "is-active", "--quiet", service]
        ).returncode == 0
        for service in all_display_services()
    )


@app.route("/api/state")
def api_state():
    settings = load_settings()
    league = settings.get("league", "worldcup")
    schedule = settings.get("display_schedule", {})

    return jsonify({
        "sport": league,
        "brightness": settings.get("brightness", 48),
        "display_running": display_running(),
        "service": service_for_league(league),
        "service_status": service_status(league),
        "schedule": {
            "enabled": schedule.get("enabled", False),
            "on_time": schedule.get("on_time", "07:00"),
            "off_time": schedule.get("off_time", "23:00"),
            "override": schedule.get("override", "auto")
        }
    })


@app.route("/api/sport/<sport>", methods=["POST"])
def api_sport(sport):
    if sport not in SPORTS:
        return jsonify({"ok": False, "error": "invalid sport"}), 400

    settings = load_settings()
    settings["league"] = sport
    save_settings(settings)

    schedule = settings.get("display_schedule", {})
    if schedule.get("override", "auto") != "off":
        run_switch(sport)

    return jsonify({"ok": True, "sport": sport})


@app.route("/api/brightness/<int:brightness>", methods=["POST"])
def api_brightness(brightness):
    brightness = max(1, min(100, brightness))

    settings = load_settings()
    settings["brightness"] = brightness
    save_settings(settings)

    league = settings.get("league", "worldcup")

    if display_running():
        service = service_for_league(league)
        development_command(["sudo", "systemctl", "restart", service])

    return jsonify({
        "ok": True,
        "brightness": brightness
    })


@app.route("/api/display/<action>", methods=["POST"])
def api_display(action):
    if action not in ("on", "off", "auto"):
        return jsonify({"ok": False, "error": "invalid action"}), 400

    settings = load_settings()
    schedule = settings.setdefault("display_schedule", {})
    schedule["override"] = action
    save_settings(settings)

    if action == "off":
        stop_all_displays()

    elif action == "on":
        run_switch(settings.get("league", "worldcup"))

    # "auto" hands control back to display_schedule.py.
    return jsonify({
        "ok": True,
        "override": action
    })


@app.route("/api/schedule", methods=["POST"])
def api_schedule():
    settings = load_settings()
    schedule = settings.setdefault("display_schedule", {})

    data = request.get_json(silent=True) or {}

    if "enabled" in data:
        schedule["enabled"] = bool(data["enabled"])

    if "on_time" in data:
        schedule["on_time"] = str(data["on_time"])

    if "off_time" in data:
        schedule["off_time"] = str(data["off_time"])

    save_settings(settings)

    return jsonify({
        "ok": True,
        "schedule": schedule
    })


@app.route("/api/restart", methods=["POST"])
def api_restart():
    settings = load_settings()
    service = service_for_league(settings.get("league", "worldcup"))
    development_command(["sudo", "systemctl", "restart", service])

    return jsonify({"ok": True, "service": service})


@app.route("/preview.png")
def preview():
    return send_file(PREVIEW_PATH, mimetype="image/png")


@app.route("/restart", methods=["POST"])
def restart():
    settings = load_settings()
    league = settings.get("league", "worldcup")
    service = service_for_league(league)

    development_command(["sudo", "systemctl", "restart", service])

    return redirect(url_for("index"))


@app.route("/refresh", methods=["POST"])
def refresh():
    settings = load_settings()
    league = settings.get("league", "worldcup")

    if league in ("worldcup", "golf"):
        development_command(["sudo", "systemctl", "restart", "sportsmatrix"])
    else:
        development_command([
            "sudo",
            "systemctl",
            "restart",
            service_for_league(league)
        ])

    return redirect(url_for("index"))


@app.route("/test-pattern", methods=["POST"])
def test_pattern():
    settings = load_settings()
    league = settings.get("league", "worldcup")

    development_command(["sudo", "systemctl", "stop", "sportsmatrix"])
    development_command(["sudo", "systemctl", "stop", "mlb-scoreboard"])
    development_command(["sudo", "systemctl", "stop", "nfl-scoreboard"])

    development_command([
        "sudo",
        "/home/scoreboard/sports/sportsmatrix_mvp/.venv/bin/python",
        "/home/scoreboard/sports/sportsmatrix_mvp/show_image.py"
    ])

    run_switch(league)

    return redirect(url_for("index"))



@app.route("/preferences/nhl", methods=["GET", "POST"])
def nhl_preferences():
    from flask import render_template_string

    settings = load_settings()
    prefs = settings.setdefault("sport_preferences", {}).setdefault("nhl", {})

    teams = [
        ("ANA","Anaheim Ducks"), ("BOS","Boston Bruins"),
        ("BUF","Buffalo Sabres"), ("CGY","Calgary Flames"),
        ("CAR","Carolina Hurricanes"), ("CHI","Chicago Blackhawks"),
        ("COL","Colorado Avalanche"), ("CBJ","Columbus Blue Jackets"),
        ("DAL","Dallas Stars"), ("DET","Detroit Red Wings"),
        ("EDM","Edmonton Oilers"), ("FLA","Florida Panthers"),
        ("LA","Los Angeles Kings"), ("MIN","Minnesota Wild"),
        ("MTL","Montreal Canadiens"), ("NSH","Nashville Predators"),
        ("NJ","New Jersey Devils"), ("NYI","New York Islanders"),
        ("NYR","New York Rangers"), ("OTT","Ottawa Senators"),
        ("PHI","Philadelphia Flyers"), ("PIT","Pittsburgh Penguins"),
        ("SJ","San Jose Sharks"), ("SEA","Seattle Kraken"),
        ("STL","St. Louis Blues"), ("TB","Tampa Bay Lightning"),
        ("TOR","Toronto Maple Leafs"), ("UTA","Utah Mammoth"),
        ("VAN","Vancouver Canucks"), ("VGK","Vegas Golden Knights"),
        ("WSH","Washington Capitals"), ("WPG","Winnipeg Jets")
    ]

    if request.method == "POST":
        team = request.form.get("favorite_team", "SJ")
        mode = request.form.get("mode", "only")
        seconds = request.form.get("favorite_seconds", "90")

        if team not in dict(teams) or mode not in ("only", "prefer", "all"):
            return "Invalid preference", 400
        if seconds not in ("60", "90", "120"):
            return "Invalid rotation duration", 400

        prefs.update({
            "favorite_team": team,
            "mode": mode,
            "favorite_seconds": int(seconds),
            "other_seconds": 30
        })
        save_settings(settings)
        return redirect(url_for("nhl_preferences"))

    return render_template_string("""
    <!doctype html>
    <html>
    <head>
    <meta name="viewport" content="width=device-width,initial-scale=1">
    <title>SportsMatrix V2 · NHL</title>
    <style>
    body{background:#080e17;color:#f5f6f8;font-family:system-ui;
         max-width:520px;margin:40px auto;padding:0 20px}
    h1{margin-bottom:4px}p{color:#a9b7c8}
    label{display:block;margin:20px 0 7px;font-weight:600}
    select{width:100%;padding:13px;background:#172333;color:white;
           border:1px solid #405268;border-radius:9px;font-size:16px}
    button{margin-top:26px;background:#e9c56c;color:#080e17;
           border:0;border-radius:9px;padding:14px 24px;
           font-size:16px;font-weight:700;cursor:pointer}
    a{color:#e9c56c}
    </style>
    </head>
    <body>
    <a href="/">SportsMatrix V2</a>
    <h1>NHL Preferences</h1>
    <p>Choose which hockey games appear on your scoreboard.</p>
    <form method="post">
      <label for="team">Favorite team</label>
      <select id="team" name="favorite_team">
      {% for code,name in teams %}
        <option value="{{code}}" {% if code == prefs.get('favorite_team','SJ') %}selected{% endif %}>{{name}}</option>
      {% endfor %}
      </select>

      <label for="mode">Viewing mode</label>
      <select id="mode" name="mode">
        <option value="only" {% if prefs.get('mode') == 'only' %}selected{% endif %}>Only my team</option>
        <option value="prefer" {% if prefs.get('mode') == 'prefer' %}selected{% endif %}>Prefer my team, rotate others</option>
        <option value="all" {% if prefs.get('mode') == 'all' %}selected{% endif %}>No preference, show all games</option>
      </select>

      <label for="seconds">Favorite game display duration</label>
      <select id="seconds" name="favorite_seconds">
      {% for n in (60,90,120) %}
        <option value="{{n}}" {% if prefs.get('favorite_seconds',90)|int == n %}selected{% endif %}>{{n}} seconds</option>
      {% endfor %}
      </select>
      <p>Other games rotate every 30 seconds.</p>
      <button type="submit">Save preferences</button>
    </form>
    </body></html>
    """, prefs=prefs, teams=teams)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8082)
