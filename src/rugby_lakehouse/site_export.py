"""Export the current Databricks Gold snapshot for a static portfolio app."""

import argparse
from collections import Counter
from datetime import date, datetime, timezone
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import re


SCHEMA_VERSION = 1
IDENTIFIER = re.compile(r"[A-Za-z_][A-Za-z0-9_]*\Z")


def _json_value(value):
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return int(value) if value == value.to_integral_value() else float(value)
    return value


def _fetch(connection, statement):
    with connection.cursor() as cursor:
        cursor.execute(statement)
        names = [column[0] for column in cursor.description]
        return [{name: _json_value(value) for name, value in zip(names, row)}
                for row in cursor.fetchall()]


def _queries(catalog, schema):
    for identifier in (catalog, schema):
        if not IDENTIFIER.fullmatch(identifier):
            raise ValueError(f"Invalid Databricks catalog or schema: {identifier!r}")
    gold = f"`{catalog}`.`{schema}`"
    return {
        "seasons": f"""
            SELECT season, source_snapshot_hash, max(ingested_at) AS ingested_at,
                   count(*) AS fixtures,
                   sum(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) AS completed,
                   sum(CASE WHEN status = 'result_unavailable' THEN 1 ELSE 0 END) AS result_unavailable
            FROM {gold}.stg_current_fixtures
            GROUP BY season, source_snapshot_hash ORDER BY season
        """,
        "teams": f"SELECT team_id, team_name FROM {gold}.dim_team ORDER BY team_name",
        "team_seasons": f"""
            SELECT g.season, g.team_id, d.team_name,
                   concat(g.season, '|', g.team_id) AS season_team_key,
                   g.played, g.wins, g.draws, g.played - g.wins - g.draws AS losses,
                   g.points_for, g.points_against,
                   g.points_for - g.points_against AS point_difference
            FROM {gold}.team_season g JOIN {gold}.dim_team d ON g.team_id = d.team_id
            ORDER BY g.season, d.team_name
        """,
        "fixtures": f"""
            SELECT match_id, season, status, played_at, round_type, round_number,
                   home_team, away_team, home_score, away_score
            FROM {gold}.fixture_schedule ORDER BY season, played_at, match_id
        """,
        "team_matches": f"""
            SELECT t.match_id, t.season, t.played_at, t.team_id, d.team_name,
                   concat(t.season, '|', t.team_id) AS season_team_key,
                   o.team_name AS opponent, t.venue, t.result,
                   t.points_for, t.points_against,
                   t.points_for - t.points_against AS point_difference
            FROM {gold}.team_match t
            JOIN {gold}.fact_match f ON t.match_id = f.match_id
            JOIN {gold}.dim_team d ON t.team_id = d.team_id
            JOIN {gold}.dim_team o ON o.team_id =
                 CASE WHEN t.venue = 'Home' THEN f.away_team_id ELSE f.home_team_id END
            ORDER BY t.season, t.played_at, t.match_id, t.venue
        """,
        "player_scoring": f"""
            SELECT p.season, p.team_id, d.team_name,
                   concat(p.season, '|', p.team_id) AS season_team_key,
                   p.player, p.tries, p.recorded_points
            FROM {gold}.player_scoring p
            JOIN {gold}.dim_team d ON p.team_id = d.team_id
            ORDER BY p.season, d.team_name, p.recorded_points DESC, p.player
        """,
        "scoring_patterns": f"""
            SELECT e.season, e.team_id, d.team_name,
                   concat(e.season, '|', e.team_id) AS season_team_key,
                   CASE WHEN e.minute <= 20 THEN '0-20'
                        WHEN e.minute <= 40 THEN '21-40'
                        WHEN e.minute <= 60 THEN '41-60'
                        WHEN e.minute <= 80 THEN '61-80'
                        ELSE '81+' END AS match_period,
                   e.event_type, count(*) AS event_count, sum(e.points) AS points
            FROM {gold}.scoring_event e
            JOIN {gold}.dim_team d ON e.team_id = d.team_id
            GROUP BY e.season, e.team_id, d.team_name,
                     CASE WHEN e.minute <= 20 THEN '0-20'
                          WHEN e.minute <= 40 THEN '21-40'
                          WHEN e.minute <= 60 THEN '41-60'
                          WHEN e.minute <= 80 THEN '61-80'
                          ELSE '81+' END,
                     e.event_type
            ORDER BY e.season, d.team_name, match_period, e.event_type
        """,
        "stadiums": f"""
            SELECT stadium AS stadium_name, count(*) AS completed_matches,
                   sum(CASE WHEN attendance IS NOT NULL THEN 1 ELSE 0 END) AS matches_with_attendance
            FROM {gold}.stg_latest_matches
            WHERE stadium IS NOT NULL
            GROUP BY stadium ORDER BY stadium
        """,
    }


def validate_bundle(data):
    """Reject a mixed or incomplete export before the site can read it."""
    seasons = data["seasons"]
    fixtures = data["fixtures"]
    team_matches = data["team_matches"]
    teams = data["teams"]
    team_seasons = data["team_seasons"]
    if not seasons or not fixtures or not team_matches:
        raise ValueError("The Gold export has no seasons, fixtures or team matches")
    if len({row["season"] for row in seasons}) != len(seasons):
        raise ValueError("Expected exactly one current snapshot per season")
    if len({row["team_id"] for row in teams}) != len(teams):
        raise ValueError("Team IDs are not unique")
    fixture_ids = {row["match_id"] for row in fixtures}
    if len(fixture_ids) != len(fixtures):
        raise ValueError("Fixture IDs are not unique")
    season_counts = Counter((row["season"], row["status"]) for row in fixtures)
    for row in seasons:
        season = row["season"]
        if row["fixtures"] != season_counts[season, "completed"] + season_counts[season, "result_unavailable"]:
            raise ValueError(f"Fixture count does not reconcile for {season}")
        if row["completed"] != season_counts[season, "completed"] or row["result_unavailable"] != season_counts[season, "result_unavailable"]:
            raise ValueError(f"Fixture status does not reconcile for {season}")
    completed = {row["match_id"]: row for row in fixtures if row["status"] == "completed"}
    for row in fixtures:
        scored = row["home_score"] is not None and row["away_score"] is not None
        if scored != (row["status"] == "completed"):
            raise ValueError(f"Fixture score/status mismatch: {row['match_id']}")
    appearances = {}
    for row in team_matches:
        match_id = row["match_id"]
        if match_id not in completed:
            raise ValueError(f"Team match has no completed fixture: {match_id}")
        appearances.setdefault(match_id, []).append(row)
    if len(appearances) != len(completed):
        raise ValueError("A completed fixture is missing team appearances")
    for match_id, sides in appearances.items():
        fixture = completed[match_id]
        by_venue = {side["venue"]: side for side in sides}
        if len(sides) != 2 or set(by_venue) != {"Home", "Away"}:
            raise ValueError(f"Expected one home and one away appearance: {match_id}")
        if (by_venue["Home"]["points_for"], by_venue["Home"]["points_against"]) != (fixture["home_score"], fixture["away_score"]):
            raise ValueError(f"Home points do not match fixture: {match_id}")
        if (by_venue["Away"]["points_for"], by_venue["Away"]["points_against"]) != (fixture["away_score"], fixture["home_score"]):
            raise ValueError(f"Away points do not match fixture: {match_id}")
    appearances_by_team = Counter((row["season"], row["team_id"]) for row in team_matches)
    if len(team_seasons) != len(appearances_by_team):
        raise ValueError("Team-season summary count does not match team appearances")
    for row in team_seasons:
        if row["played"] != appearances_by_team[row["season"], row["team_id"]]:
            raise ValueError(f"Team-season appearances do not reconcile: {row['season']} {row['team_name']}")
    event_points = sum(row["points"] for row in data["scoring_patterns"])
    match_points = sum(row["home_score"] + row["away_score"] for row in completed.values())
    return {
        "fixtures": len(fixtures),
        "completed_matches": len(completed),
        "result_unavailable": len(fixtures) - len(completed),
        "team_appearances": len(team_matches),
        "listed_scoring_events": sum(row["event_count"] for row in data["scoring_patterns"]),
        "listed_event_points": event_points,
        "final_score_points": match_points,
        "score_event_points_gap": match_points - event_points,
    }


def export_site_data(connection, output_dir):
    """Write one immutable snapshot, then publish its manifest last."""
    statements = _queries(os.getenv("RUGBY_DATABRICKS_CATALOG", "workspace"),
                          os.getenv("RUGBY_DATABRICKS_GOLD_SCHEMA", "rugby_dbt"))
    data = {name: _fetch(connection, query) for name, query in statements.items()}
    if data["seasons"] != _fetch(connection, statements["seasons"]):
        raise ValueError("The current source snapshot changed during export; retry")
    quality = validate_bundle(data)
    output_dir = Path(output_dir)
    snapshot_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    snapshot_dir = output_dir / "snapshots" / snapshot_id
    snapshot_dir.mkdir(parents=True, exist_ok=False)
    datasets = {}
    for name, rows in data.items():
        payload = (json.dumps(rows, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")
        target = snapshot_dir / f"{name}.json"
        target.write_bytes(payload)
        datasets[name] = {"path": f"snapshots/{snapshot_id}/{name}.json",
                          "rows": len(rows), "sha256": hashlib.sha256(payload).hexdigest()}
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": "Databricks current-snapshot dbt Gold",
        "seasons": data["seasons"],
        "datasets": datasets,
        "quality": quality,
        "notes": ["Results unavailable in the source are not labelled upcoming.",
                  "Listed scoring events can be incomplete even when a final score exists.",
                  "Stadium coordinates have not yet been verified; no map points are exported."],
    }
    temporary_manifest = output_dir / "manifest.json.tmp"
    temporary_manifest.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary_manifest.replace(output_dir / "manifest.json")
    return manifest


def main():
    parser = argparse.ArgumentParser(description="Export Databricks Gold for a static rugby portfolio app")
    parser.add_argument("--output", type=Path, default=Path("data/site-export"))
    args = parser.parse_args()
    host = os.getenv("DATABRICKS_HOST", "").removeprefix("https://").rstrip("/")
    http_path = os.getenv("DATABRICKS_HTTP_PATH")
    if not host or not http_path:
        parser.error("Set DATABRICKS_HOST and DATABRICKS_HTTP_PATH")
    from databricks import sql  # Optional site-export dependency; loaded only by the CLI.
    from databricks.sdk.core import Config
    config = Config(host=f"https://{host}", auth_type="external-browser")
    with sql.connect(server_hostname=host, http_path=http_path,
                     credentials_provider=lambda: config.authenticate) as connection:
        manifest = export_site_data(connection, args.output)
    print(json.dumps({"output": str(args.output / "manifest.json"),
                      "quality": manifest["quality"],
                      "datasets": {key: value["rows"] for key, value in manifest["datasets"].items()}},
                     indent=2))


if __name__ == "__main__":
    main()
