"""Validate source records and derive stable business keys."""

from datetime import datetime
import hashlib
import json

COMPETITION = "United Rugby Championship"
SEASON = "2024-25"


def canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def digest(value: object) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def normalize_match(raw: dict) -> dict:
    try:
        home, away = raw["home"], raw["away"]
        home_team, away_team = home["team"].strip(), away["team"].strip()
        if not home_team or not away_team or home_team == away_team:
            raise ValueError("Home and away teams must be distinct and nonempty")
        played_at = datetime.fromisoformat(raw["date"].replace("Z", "+00:00"))
        home_score, away_score = int(home["score"]), int(away["score"])
        if home_score < 0 or away_score < 0:
            raise ValueError("Scores cannot be negative")
        round_type = str(raw["round_type"])
        round_number = int(raw["round"])
    except (KeyError, TypeError, AttributeError, ValueError) as exc:
        raise ValueError(f"Invalid match: {exc}") from exc

    # The source has no fixture ID. Round, phase and teams survive score/date corrections.
    identity = [COMPETITION, SEASON, round_type, round_number, home_team, away_team]
    match_id = digest(identity)[:24]
    players = []
    scoring_events = []
    for side, team in (("home", home), ("away", away)):
        for jersey, player in (team.get("lineup") or {}).items():
            name = player.get("name") if isinstance(player, dict) else None
            if name:
                players.append({"side": side, "team": team["team"], "jersey": str(jersey), "player": name.strip()})
        for ordinal, event in enumerate(team.get("scores") or []):
            scoring_events.append({
                "event_id": digest([match_id, side, ordinal])[:24],
                "side": side,
                "team": team["team"],
                "minute": event.get("minute"),
                "event_type": event.get("type"),
                "player": event.get("player"),
                "points": int(event.get("value") or 0),
            })
    return {
        "match_id": match_id,
        "competition": COMPETITION,
        "season": SEASON,
        "round_type": round_type,
        "round_number": round_number,
        "played_at": played_at.isoformat(),
        "home_team": home_team,
        "away_team": away_team,
        "home_score": home_score,
        "away_score": away_score,
        "stadium": raw.get("stadium"),
        "attendance": raw.get("attendance"),
        "players": players,
        "scoring_events": scoring_events,
        "source_hash": digest(raw),
    }

