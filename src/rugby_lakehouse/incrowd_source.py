"""Build a local URC season snapshot from the feed used by Rugby-Data.

The output has the same fixture shape as the community JSON, so the existing
landing-file command can ingest it without a separate transformation path.
"""

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .source import source_file
from .transform import normalize_match


API_ROOT = "https://rugby-union-feeds.incrowdsports.com/v1/matches"
COMPETITION_ID = 1068
PROVIDER = "rugbyviz"
SCORING_POINTS = {
    "Try": 5, "Penalty Try": 5, "Penalty": 3, "Conversion": 2,
    "Drop goal": 3, "Missed drop goal": 0, "Missed penalty": 0,
    "Missed conversion": 0,
}


def fetch_json(url, attempts=3):
    """Retry transient errors; never turn an unsuccessful response into data."""
    for attempt in range(attempts):
        try:
            request = Request(url, headers={"User-Agent": "rugby-analytics-lakehouse/0.1",
                                            "Accept": "application/json"})
            with urlopen(request, timeout=30) as response:
                return json.load(response)
        except HTTPError as exc:
            if exc.code not in (429, 500, 502, 503, 504) or attempt == attempts - 1:
                raise
            retry_after = exc.headers.get("Retry-After", "")
            delay = min(float(retry_after), 30) if retry_after.isdigit() else 2 ** attempt
        except (URLError, TimeoutError):
            if attempt == attempts - 1:
                raise
            delay = 2 ** attempt
        time.sleep(delay)
    raise RuntimeError("Unreachable retry state")


def _players_and_events(detail):
    lineups = {"home": {}, "away": {}}
    scores = {"home": [], "away": []}
    player_names = {}
    positions = {}
    team_ids = {side: detail[f"{side}Team"]["id"] for side in ("home", "away")}
    if team_ids["home"] == team_ids["away"]:
        raise ValueError(f"Match {detail['id']} has the same team on both sides")

    for side in ("home", "away"):
        for player in detail[f"{side}Team"].get("players") or []:
            player_id = player["id"]
            position = str(player["positionId"])
            player_names[player_id] = player.get("name")
            positions[player_id] = (side, position)
            lineups[side][position] = {
                "name": player.get("name"),
                "on": [0] if position.isdigit() and int(position) <= 15 else [],
                "off": [], "reds": [], "yellows": [],
            }

    for event in detail.get("events") or []:
        team_id = event.get("teamId")
        if team_id not in team_ids.values():
            continue
        side = "home" if team_id == team_ids["home"] else "away"
        event_type = event.get("type")
        player_id = event.get("playerId")
        minute = event.get("minute", 0)
        if event_type in SCORING_POINTS:
            scores[side].append({"minute": minute, "type": event_type,
                                 "player": player_names.get(player_id),
                                 "value": SCORING_POINTS[event_type]})
        elif player_id in positions and positions[player_id][0] == side:
            record = lineups[side][positions[player_id][1]]
            field = {"Sub On": "on", "Sub Off": "off",
                     "Yellow card": "yellows", "Red card": "reds"}.get(event_type)
            if field:
                record[field].append(minute)
    return lineups, scores


def convert_match(summary, detail):
    """Map one API match into the existing source-JSON fixture shape."""
    if summary["id"] != detail["id"]:
        raise ValueError("Summary and detail match IDs differ")
    if summary["date"] != detail["date"]:
        raise ValueError(f"Summary and detail dates differ for match {summary['id']}")
    if summary.get("status", "").lower() not in {"result", "complete", "completed", "finished", "fulltime", "ft"}:
        raise ValueError(f"Match {summary['id']} does not have a final result")
    lineups, scores = _players_and_events(detail)
    fixture = {
        "api_match_id": summary["id"],
        "date": detail["date"],
        "round": detail["round"],
        "round_type": "league" if detail.get("roundTypeId") == 1 else "knockout",
        "stadium": (detail.get("venue") or {}).get("name"),
        "attendance": detail.get("attendance"),
    }
    for side in ("home", "away"):
        brief, full = summary[f"{side}Team"], detail[f"{side}Team"]
        if brief["id"] != full["id"]:
            raise ValueError(f"Team ID changed between responses for match {summary['id']}")
        score = full.get("score")
        if score is None or brief.get("score") != score:
            raise ValueError(f"Missing or inconsistent {side} score for match {summary['id']}")
        fixture[side] = {"team": full["name"], "score": score,
                         "conference": full.get("group"),
                         "lineup": lineups[side], "scores": scores[side]}
    return fixture


def build_season(season, fetch=fetch_json, cache_dir=None, delay_seconds=0.2,
                 refresh_cache=False):
    """Fetch the season index and each completed match's detailed events."""
    source_file(season)
    year = season[:4]
    params = f"season={year}01&provider={PROVIDER}"
    index = fetch(f"{API_ROOT}?compId={COMPETITION_ID}&{params}")
    summaries = index.get("data")
    if not isinstance(summaries, list) or not summaries:
        raise ValueError("The URC feed returned no season fixtures")
    if len({row["id"] for row in summaries}) != len(summaries):
        raise ValueError("The URC feed returned duplicate match IDs")
    cache_dir = Path(cache_dir) if cache_dir else None
    fixtures = []
    for row in summaries:
        match_id = row["id"]
        cache_file = cache_dir / f"{match_id}.json" if cache_dir else None
        cached = bool(cache_file and cache_file.exists() and not refresh_cache)
        if cached:
            detail = json.loads(cache_file.read_text(encoding="utf-8"))
        else:
            if delay_seconds:
                time.sleep(delay_seconds)
            response = fetch(f"{API_ROOT}/{match_id}?{params}")
            detail = response.get("data")
            if not isinstance(detail, dict):
                raise ValueError(f"No detail returned for match {match_id}")
        fixture = convert_match(row, detail)
        if cache_file and not cached:
            cache_file.parent.mkdir(parents=True, exist_ok=True)
            temporary = cache_file.with_suffix(".json.tmp")
            temporary.write_text(json.dumps(detail, ensure_ascii=False), encoding="utf-8")
            temporary.replace(cache_file)
        fixtures.append(fixture)
    normalized = [normalize_match(row, season, i) for i, row in enumerate(fixtures)]
    if len({row["match_id"] for row in normalized}) != len(normalized):
        raise ValueError("The new snapshot has duplicate fixture keys")
    if any(row["status"] != "completed" for row in normalized):
        raise ValueError("The requested season still has fixtures without results")
    return fixtures


def save_season(fixtures, output):
    """Publish a validated local JSON file atomically."""
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = (json.dumps(fixtures, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    temporary = output.with_suffix(output.suffix + ".tmp")
    try:
        temporary.write_bytes(payload)
        temporary.replace(output)
    finally:
        temporary.unlink(missing_ok=True)
    return hashlib.sha256(payload).hexdigest()


def main():
    parser = argparse.ArgumentParser(description="Fetch a completed URC season from the underlying match feed")
    parser.add_argument("--season", default="2025-26")
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    parser.add_argument("--refresh-cache", action="store_true",
                        help="Re-fetch match details, including any corrected events")
    args = parser.parse_args()
    source_file(args.season)
    start = int(args.season[:4])
    output = args.data_dir / "source" / f"celtic-{start}-{start + 1}-api.json"
    fixtures = build_season(args.season, cache_dir=args.data_dir / "api-cache" / args.season,
                            refresh_cache=args.refresh_cache)
    sha256 = save_season(fixtures, output)
    print(json.dumps({"output": str(output), "sha256": sha256,
                      "fixtures": len(fixtures),
                      "completed": len(fixtures),
                      "player_appearances": sum(len(row[s]["lineup"]) for row in fixtures for s in ("home", "away")),
                      "listed_scoring_events": sum(len(row[s]["scores"]) for row in fixtures for s in ("home", "away")),
                      "extracted_at": datetime.now(timezone.utc).isoformat()}, indent=2))


if __name__ == "__main__":
    main()
