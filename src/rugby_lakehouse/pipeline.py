"""Local reference pipeline: immutable Bronze events, current Silver, analytical Gold."""

from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3

from .transform import SEASON, TRANSFORM_VERSION, canonical_json, digest, normalize_match

SCHEMA = """
CREATE TABLE IF NOT EXISTS bronze_event (
  event_id INTEGER PRIMARY KEY AUTOINCREMENT,
  match_id TEXT NOT NULL,
  source_hash TEXT NOT NULL,
  ingested_at TEXT NOT NULL,
  payload TEXT NOT NULL,
  UNIQUE(match_id, source_hash)
);
CREATE TABLE IF NOT EXISTS silver_fixture (
  match_id TEXT PRIMARY KEY, season TEXT NOT NULL, source_index INTEGER NOT NULL,
  status TEXT NOT NULL, played_at TEXT NOT NULL, round_type TEXT NOT NULL,
  round_number INTEGER NOT NULL, home_team TEXT NOT NULL, away_team TEXT NOT NULL,
  home_score INTEGER, away_score INTEGER, source_hash TEXT NOT NULL,
  snapshot_hash TEXT NOT NULL, transform_version INTEGER NOT NULL,
  UNIQUE(season, source_index)
);
CREATE TABLE IF NOT EXISTS silver_match (
  match_id TEXT PRIMARY KEY, competition TEXT NOT NULL, season TEXT NOT NULL,
  round_type TEXT NOT NULL, round_number INTEGER NOT NULL, played_at TEXT NOT NULL,
  home_team TEXT NOT NULL, away_team TEXT NOT NULL,
  home_score INTEGER NOT NULL, away_score INTEGER NOT NULL,
  stadium TEXT, attendance INTEGER, source_hash TEXT NOT NULL, updated_at TEXT NOT NULL,
  transform_version INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS silver_player_appearance (
  match_id TEXT NOT NULL, side TEXT NOT NULL, jersey TEXT NOT NULL,
  team TEXT NOT NULL, player TEXT NOT NULL,
  PRIMARY KEY(match_id, side, jersey)
);
CREATE TABLE IF NOT EXISTS silver_scoring_event (
  event_id TEXT PRIMARY KEY, match_id TEXT NOT NULL, side TEXT NOT NULL,
  team TEXT NOT NULL, minute INTEGER, event_type TEXT, player TEXT, points INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS dim_team (
  team_id TEXT PRIMARY KEY, team_name TEXT NOT NULL UNIQUE
);
CREATE TABLE IF NOT EXISTS fact_match (
  match_id TEXT PRIMARY KEY, season TEXT NOT NULL, played_at TEXT NOT NULL,
  home_team_id TEXT NOT NULL, away_team_id TEXT NOT NULL,
  home_score INTEGER NOT NULL, away_score INTEGER NOT NULL,
  winner_team_id TEXT, attendance INTEGER
);
CREATE TABLE IF NOT EXISTS gold_team_season (
  season TEXT NOT NULL, team_id TEXT NOT NULL,
  played INTEGER NOT NULL, wins INTEGER NOT NULL, draws INTEGER NOT NULL,
  points_for INTEGER NOT NULL, points_against INTEGER NOT NULL,
  PRIMARY KEY(season, team_id)
);
"""


def _team_id(name: str) -> str:
    from .transform import digest
    return digest(name)[:16]


def _refresh_gold(db: sqlite3.Connection) -> None:
    db.execute("DELETE FROM dim_team")
    db.execute("DELETE FROM fact_match")
    db.execute("DELETE FROM gold_team_season")
    for (name,) in db.execute("SELECT home_team FROM silver_match UNION SELECT away_team FROM silver_match"):
        db.execute("INSERT INTO dim_team VALUES (?, ?)", (_team_id(name), name))
    for m in db.execute("SELECT match_id, season, played_at, home_team, away_team, home_score, away_score, attendance FROM silver_match").fetchall():
        mid, season, played, home, away, hs, aws, attendance = m
        winner = home if hs > aws else away if aws > hs else None
        db.execute("INSERT INTO fact_match VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                   (mid, season, played, _team_id(home), _team_id(away), hs, aws,
                    _team_id(winner) if winner else None, attendance))
    db.execute("""INSERT INTO gold_team_season
      SELECT season, team_id, COUNT(*), SUM(win), SUM(draw), SUM(pf), SUM(pa)
      FROM (
        SELECT season, home_team_id team_id, home_score > away_score win,
               home_score = away_score draw, home_score pf, away_score pa FROM fact_match
        UNION ALL
        SELECT season, away_team_id, away_score > home_score,
               home_score = away_score, away_score, home_score FROM fact_match
      ) GROUP BY season, team_id""")


def _export_bronze(database: Path, bronze_dir: Path) -> None:
    """Repair missing files from the durable SQLite event ledger on every run."""
    with sqlite3.connect(database) as db:
        events = db.execute(
            "SELECT event_id, match_id, source_hash, ingested_at, payload FROM bronze_event"
        ).fetchall()
    for event_id, match_id, source_hash, ingested_at, payload in events:
        target = bronze_dir / f"{event_id:08d}.jsonl"
        if target.exists():
            continue
        temporary = target.with_suffix(".tmp")
        temporary.write_text(canonical_json({
            "match_id": match_id, "source_hash": source_hash,
            "ingested_at": ingested_at, "payload": json.loads(payload),
        }) + "\n", encoding="utf-8")
        temporary.replace(target)


def run(matches: list[dict], database: Path, bronze_dir: Path, season: str = SEASON) -> dict[str, int]:
    normalized = [normalize_match(match, season, index) for index, match in enumerate(matches)]
    ids = [match["match_id"] for match in normalized]
    if len(ids) != len(set(ids)):
        raise ValueError("Source snapshot contains duplicate fixture keys")
    database.parent.mkdir(parents=True, exist_ok=True)
    bronze_dir.mkdir(parents=True, exist_ok=True)
    ingested_at = datetime.now(timezone.utc).isoformat()
    snapshot_hash = digest(matches)
    changed = []
    with sqlite3.connect(database) as db:
        db.executescript(SCHEMA)
        # Existing local databases predate the transform-version column.
        columns = {row[1] for row in db.execute("PRAGMA table_info(silver_match)")}
        if "transform_version" not in columns:
            db.execute("ALTER TABLE silver_match ADD COLUMN transform_version INTEGER NOT NULL DEFAULT 1")
        previous = {row[0]: (row[1], row[2], row[3]) for row in db.execute(
            "SELECT match_id, source_hash, status, transform_version FROM silver_fixture WHERE season = ?", (season,)
        )}
        current_ids = set(ids)
        removed = len(previous.keys() - current_ids)
        db.execute("DELETE FROM silver_fixture WHERE season = ?", (season,))
        for raw, match in zip(matches, normalized):
            db.execute("""INSERT INTO silver_fixture VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                       (match["match_id"], season, match["source_index"], match["status"],
                        match["played_at"], match["round_type"], match["round_number"],
                        match["home_team"], match["away_team"], match["home_score"],
                        match["away_score"], match["source_hash"], snapshot_hash, TRANSFORM_VERSION))
            prior = previous.get(match["match_id"])
            current = db.execute("SELECT source_hash, transform_version FROM silver_match WHERE match_id = ?", (match["match_id"],)).fetchone()
            unchanged = (prior == (match["source_hash"], match["status"], TRANSFORM_VERSION)
                         and (match["status"] == "result_unavailable" or current == (match["source_hash"], TRANSFORM_VERSION)))
            if unchanged:
                continue
            changed.append((raw, match))
            db.execute("INSERT OR IGNORE INTO bronze_event(match_id, source_hash, ingested_at, payload) VALUES (?, ?, ?, ?)",
                       (match["match_id"], match["source_hash"], ingested_at, canonical_json(raw)))
            if match["status"] == "result_unavailable":
                continue
            db.execute("""INSERT INTO silver_match VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(match_id) DO UPDATE SET
                played_at=excluded.played_at, home_score=excluded.home_score,
                away_score=excluded.away_score, stadium=excluded.stadium,
                attendance=excluded.attendance, source_hash=excluded.source_hash,
                transform_version=excluded.transform_version,
                updated_at=excluded.updated_at""",
                       (match["match_id"], match["competition"], match["season"], match["round_type"],
                        match["round_number"], match["played_at"], match["home_team"], match["away_team"],
                        match["home_score"], match["away_score"], match["stadium"], match["attendance"],
                        match["source_hash"], ingested_at, TRANSFORM_VERSION))
            db.execute("DELETE FROM silver_player_appearance WHERE match_id = ?", (match["match_id"],))
            db.execute("DELETE FROM silver_scoring_event WHERE match_id = ?", (match["match_id"],))
            db.executemany("INSERT INTO silver_player_appearance VALUES (?, ?, ?, ?, ?)",
                           [(match["match_id"], p["side"], p["jersey"], p["team"], p["player"]) for p in match["players"]])
            db.executemany("INSERT INTO silver_scoring_event VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                           [(e["event_id"], match["match_id"], e["side"], e["team"], e["minute"],
                             e["event_type"], e["player"], e["points"]) for e in match["scoring_events"]])
        completed_ids = {match["match_id"] for match in normalized if match["status"] == "completed"}
        obsolete = [row[0] for row in db.execute(
            "SELECT match_id FROM silver_match WHERE season = ?", (season,)
        ) if row[0] not in completed_ids]
        for match_id in obsolete:
            db.execute("DELETE FROM silver_match WHERE match_id = ?", (match_id,))
            db.execute("DELETE FROM silver_player_appearance WHERE match_id = ?", (match_id,))
            db.execute("DELETE FROM silver_scoring_event WHERE match_id = ?", (match_id,))
        if changed or removed or obsolete:
            _refresh_gold(db)
        db.commit()
    _export_bronze(database, bronze_dir)
    return {"source_fixtures": len(matches), "source_matches": len(matches),
            "completed_matches": len(completed_ids), "fixtures_without_result": len(matches) - len(completed_ids),
            "changed_matches": len(changed), "removed_fixtures": removed}


def summary(database: Path, season: str | None = None) -> list[dict]:
    with sqlite3.connect(database) as db:
        return [dict(zip(("season", "team", "played", "wins", "draws", "points_for", "points_against"), row))
                for row in db.execute("""SELECT g.season, d.team_name, g.played, g.wins, g.draws, g.points_for, g.points_against
                    FROM gold_team_season g JOIN dim_team d ON d.team_id = g.team_id
                    WHERE (? IS NULL OR g.season = ?)
                    ORDER BY g.season DESC, g.wins DESC, (g.points_for - g.points_against) DESC, d.team_name""",
                    (season, season))]


def quality(database: Path) -> dict:
    with sqlite3.connect(database) as db:
        completed = db.execute("SELECT COUNT(*) FROM silver_match").fetchone()[0]
        unavailable = db.execute("SELECT COUNT(*) FROM silver_fixture WHERE status = 'result_unavailable'").fetchone()[0]
        by_season = [dict(zip(("season", "source_fixtures", "completed_matches", "fixtures_without_result"), row))
                     for row in db.execute("""SELECT season, COUNT(*),
                       SUM(status = 'completed'), SUM(status = 'result_unavailable')
                       FROM silver_fixture GROUP BY season ORDER BY season""")]
        appearances = db.execute("SELECT COUNT(*) FROM silver_player_appearance").fetchone()[0]
        events = db.execute("SELECT COUNT(*) FROM silver_scoring_event").fetchone()[0]
        mismatches = db.execute("""
            SELECT m.match_id, m.season, m.home_team, m.home_score, COALESCE(h.points, 0),
                   m.away_team, m.away_score, COALESCE(a.points, 0)
            FROM silver_match m
            LEFT JOIN (SELECT match_id, SUM(points) points FROM silver_scoring_event
                       WHERE side = 'home' GROUP BY match_id) h ON h.match_id = m.match_id
            LEFT JOIN (SELECT match_id, SUM(points) points FROM silver_scoring_event
                       WHERE side = 'away' GROUP BY match_id) a ON a.match_id = m.match_id
            WHERE m.home_score != COALESCE(h.points, 0)
               OR m.away_score != COALESCE(a.points, 0)
            ORDER BY m.played_at
        """).fetchall()
    return {
        "fixtures": completed,
        "completed_matches": completed,
        "fixtures_without_result": unavailable,
        "source_fixtures": completed + unavailable,
        "by_season": by_season,
        "player_appearances": appearances,
        "scoring_events": events,
        "fixtures_with_score_event_discrepancy": len(mismatches),
        "sample_discrepancies": [
            {"match_id": row[0], "season": row[1], "home_team": row[2], "home_score": row[3],
             "home_event_points": row[4], "away_team": row[5], "away_score": row[6],
             "away_event_points": row[7]} for row in mismatches[:5]
        ],
    }

