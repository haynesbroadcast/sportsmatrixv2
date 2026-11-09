"""Reusable favorite-team selection and duration policy."""
from datetime import datetime, timezone

def is_favorite(event, favorite):
    if not favorite: return False
    aliases = {"SJ": {"SJ", "SJS"}, "SJS": {"SJ", "SJS"}}
    wanted = aliases.get(favorite.upper(), {favorite.upper()})
    return any(str(c.get("team",{}).get("abbreviation", "")).upper() in wanted
               for competition in event.get("competitions", [])
               for c in competition.get("competitors", []))

def choose(events, prefs):
    mode = prefs.get("mode", "all")
    favorite = prefs.get("favorite_team", "")
    if mode != "only" or not favorite:
        return list(events)
    matches = [e for e in events if is_favorite(e, favorite)]
    live = [e for e in matches if e.get("status",{}).get("type",{}).get("state") == "in"]
    future = [e for e in matches if e.get("status",{}).get("type",{}).get("state") == "pre"]
    finals = [e for e in matches if e.get("status",{}).get("type",{}).get("state") == "post"]
    future.sort(key=lambda e: e.get("date", ""))
    finals.sort(key=lambda e: e.get("date", ""), reverse=True)
    return live or future[:1] or finals[:1]

def duration(event, prefs):
    if prefs.get("mode") == "prefer" and is_favorite(event, prefs.get("favorite_team", "")):
        return prefs.get("favorite_seconds", 90)
    return prefs.get("other_seconds", 30)
