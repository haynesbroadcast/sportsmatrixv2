"""Atomic configuration storage with validation and a per-process lock."""
import json
import os
import tempfile
import threading
from pathlib import Path
from .registry import supported, PROFILES

_LOCK = threading.RLock()
DEFAULT = {"league":"nhl", "brightness":50, "power":"on", "profile":"enhanced_128x64", "schedule":{"enabled":False,"on":"08:00","off":"22:00"}, "sport_preferences":{"nhl":{"favorite_team":"SJ", "mode":"only", "favorite_seconds":90, "other_seconds":30}}}

class ConfigStore:
    def __init__(self, path):
        self.path = Path(path)
    def read(self):
        with _LOCK:
            if not self.path.exists():
                return json.loads(json.dumps(DEFAULT))
            data = json.loads(self.path.read_text())
            data.setdefault("power", "on")
            data.setdefault("schedule", {"enabled": False, "on": "08:00", "off": "22:00"})
            data.setdefault("sport_preferences", {})
            data.setdefault("profile", "enhanced_128x64" if data.get("display",{}).get("cols",128)==128 else "compact_64x32")
            return data
    def update(self, patch):
        with _LOCK:
            data = self.read()
            if "league" in patch and patch["league"] not in supported():
                raise ValueError("Unsupported or unavailable league")
            if "brightness" in patch:
                value = patch["brightness"]
                if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= 100:
                    raise ValueError("Brightness must be an integer from 1 to 100")
            if "power" in patch and patch["power"] not in ("on", "off", "auto"):
                raise ValueError("Power must be on, off, or auto")
            if "profile" in patch and patch["profile"] not in PROFILES:
                raise ValueError("Unknown display profile")
            if "schedule" in patch:
                schedule = patch["schedule"]
                if not isinstance(schedule, dict) or set(schedule) - {"enabled", "on", "off"}:
                    raise ValueError("Invalid schedule")
                if "enabled" in schedule and type(schedule["enabled"]) is not bool:
                    raise ValueError("Schedule enabled must be boolean")
                import re
                for field in ("on", "off"):
                    if field in schedule and (not isinstance(schedule[field], str) or not re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", schedule[field])):
                        raise ValueError("Schedule time must be HH:MM")
            if "sport_preferences" in patch:
                prefs = patch["sport_preferences"]
                if not isinstance(prefs, dict): raise ValueError("Invalid preferences")
                for league, choice in prefs.items():
                    if league not in supported() or not isinstance(choice, dict):
                        raise ValueError("Invalid league preferences")
                    if choice.get("mode", "all") not in ("all", "only", "prefer"):
                        raise ValueError("Invalid preference mode")
                    teams = choice.get("favorite_team_ids", [])
                    if not isinstance(teams, list) or len(teams) > 30 or any(not isinstance(x, str) or not x.isdigit() or len(x)>12 for x in teams):
                        raise ValueError("Invalid favorite team IDs")
                    team = choice.get("favorite_team", "")
                    if not isinstance(team, str) or len(team) > 32:
                        raise ValueError("Invalid favorite")
                    for field in ("favorite_seconds", "other_seconds"):
                        if field in choice and (type(choice[field]) is not int or not 5 <= choice[field] <= 600):
                            raise ValueError("Invalid rotation duration")
            for key in ("league", "brightness", "power", "profile"):
                if key in patch: data[key] = patch[key]
            if "schedule" in patch:
                data.setdefault("schedule", {}).update(patch["schedule"])
            if "sport_preferences" in patch:
                for league, choice in patch["sport_preferences"].items():
                    data["sport_preferences"].setdefault(league, {}).update(choice)
            self.path.parent.mkdir(parents=True, exist_ok=True)
            fd, tmp = tempfile.mkstemp(prefix=".settings-", dir=self.path.parent)
            try:
                with os.fdopen(fd, "w") as stream:
                    json.dump(data, stream, indent=2)
                    stream.write("\n")
                    stream.flush(); os.fsync(stream.fileno())
                os.replace(tmp, self.path)
            finally:
                if os.path.exists(tmp): os.unlink(tmp)
            return data
