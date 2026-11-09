import json
from pathlib import Path
from flask import Flask, render_template, request, redirect, url_for
from werkzeug.utils import secure_filename

app = Flask(__name__)
ROOT = Path(__file__).resolve().parents[1]
SETTINGS = ROOT / "config/settings.json"


def load_settings():
    return json.loads(SETTINGS.read_text())


def save_settings(settings):
    SETTINGS.write_text(json.dumps(settings, indent=2))


@app.route("/", methods=["GET", "POST"])
def index():
    settings = load_settings()

    if request.method == "POST":
        settings["league"] = request.form.get("league", settings["league"])
        settings["favorite_team"] = request.form.get("favorite_team", settings["favorite_team"]).upper()
        settings["brightness"] = int(request.form.get("brightness", settings["brightness"]))
        settings["refresh_seconds"] = int(request.form.get("refresh_seconds", settings["refresh_seconds"]))
        save_settings(settings)
        return redirect(url_for("index"))

    return render_template("index.html", settings=settings)


@app.route("/upload-logo", methods=["POST"])
def upload_logo():
    league = request.form.get("league", "worldcup")
    abbr = request.form.get("abbr", "").upper().strip()
    file = request.files.get("logo")

    if not abbr or not file:
        return redirect(url_for("index"))

    folder = ROOT / "assets" / ("flags" if league == "worldcup" else f"logos/{league}")
    folder.mkdir(parents=True, exist_ok=True)

    filename = secure_filename(f"{abbr}.png")
    file.save(folder / filename)

    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
