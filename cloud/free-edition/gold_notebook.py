# Databricks notebook source
"""Build season-level rugby marts from the latest Silver match versions."""

import re


dbutils.widgets.text("catalog", "workspace")
dbutils.widgets.text("schema", "rugby_analytics")
catalog = dbutils.widgets.get("catalog")
schema = dbutils.widgets.get("schema")
for name in (catalog, schema):
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
        raise ValueError(f"Invalid catalog or schema name: {name!r}")

namespace = f"`{catalog}`.`{schema}`"
silver_matches = f"{namespace}.`silver_match_versions`"
silver_events = f"{namespace}.`silver_scoring_versions`"
for table in ("silver_match_versions", "silver_scoring_versions"):
    if not spark.catalog.tableExists(f"{catalog}.{schema}.{table}"):  # noqa: F821
        raise ValueError(f"Run the ingestion notebook first: {catalog}.{schema}.{table} is missing")

spark.sql(f"""
CREATE OR REPLACE TEMP VIEW rugby_latest_matches AS
SELECT * EXCEPT (version_rank)
FROM (
  SELECT *, row_number() OVER (
    PARTITION BY match_id
    ORDER BY ingested_at DESC, transform_version DESC, source_hash DESC
  ) AS version_rank
  FROM {silver_matches}
)
WHERE version_rank = 1
""")

spark.sql(f"""
CREATE OR REPLACE TABLE {namespace}.`dim_team` USING DELTA AS
SELECT sha2(team_name, 256) AS team_id, team_name
FROM (
  SELECT home_team AS team_name FROM rugby_latest_matches
  UNION
  SELECT away_team AS team_name FROM rugby_latest_matches
)
""")

spark.sql(f"""
CREATE OR REPLACE TABLE {namespace}.`fact_match` USING DELTA AS
SELECT match_id, season, round_type, round_number, played_at,
       sha2(home_team, 256) AS home_team_id,
       sha2(away_team, 256) AS away_team_id,
       home_score, away_score, attendance,
       CASE WHEN home_score > away_score THEN sha2(home_team, 256)
            WHEN away_score > home_score THEN sha2(away_team, 256)
       END AS winner_team_id
FROM rugby_latest_matches
""")

spark.sql(f"""
CREATE OR REPLACE TABLE {namespace}.`gold_team_season` USING DELTA AS
WITH sides AS (
  SELECT season, home_team_id AS team_id, home_score AS points_for,
         away_score AS points_against,
         CASE WHEN home_score > away_score THEN 1 ELSE 0 END AS win,
         CASE WHEN home_score = away_score THEN 1 ELSE 0 END AS draw
  FROM {namespace}.`fact_match`
  UNION ALL
  SELECT season, away_team_id, away_score, home_score,
         CASE WHEN away_score > home_score THEN 1 ELSE 0 END,
         CASE WHEN away_score = home_score THEN 1 ELSE 0 END
  FROM {namespace}.`fact_match`
)
SELECT season, team_id, count(*) AS played, sum(win) AS wins,
       sum(draw) AS draws, sum(points_for) AS points_for,
       sum(points_against) AS points_against
FROM sides
GROUP BY season, team_id
""")

spark.sql(f"""
CREATE OR REPLACE TABLE {namespace}.`gold_player_scoring` USING DELTA AS
SELECT m.season, sha2(e.team, 256) AS team_id, e.player,
       sum(CASE WHEN e.event_type = 'Try' THEN 1 ELSE 0 END) AS tries,
       sum(e.points) AS recorded_points
FROM {silver_events} e
JOIN rugby_latest_matches m
  ON e.match_id = m.match_id
 AND e.source_hash = m.source_hash
 AND e.transform_version = m.transform_version
WHERE e.player IS NOT NULL AND trim(e.player) <> ''
GROUP BY m.season, e.team, e.player
""")

checks = spark.sql(f"""
SELECT
  (SELECT count(*) FROM rugby_latest_matches) AS current_matches,
  (SELECT count(*) FROM {namespace}.`fact_match`) AS fact_matches,
  (SELECT count(*) FROM {namespace}.`dim_team`) AS teams,
  (SELECT sum(played) FROM {namespace}.`gold_team_season`) AS team_appearances,
  (SELECT sum(points_for) FROM {namespace}.`gold_team_season`) AS team_points_for,
  (SELECT sum(home_score + away_score) FROM {namespace}.`fact_match`) AS match_points
""").first()
if checks.current_matches == 0 or checks.fact_matches != checks.current_matches:
    raise ValueError("Gold fact count does not match the current Silver matches")
if checks.team_appearances != 2 * checks.fact_matches:
    raise ValueError("Team-season appearances do not reconcile with match count")
if checks.team_points_for != checks.match_points:
    raise ValueError("Team-season points do not reconcile with match scores")

print(checks.asDict())
spark.sql(f"""
SELECT d.team_name, g.played, g.wins, g.draws, g.points_for, g.points_against
FROM {namespace}.`gold_team_season` g
JOIN {namespace}.`dim_team` d ON g.team_id = d.team_id
ORDER BY g.wins DESC, (g.points_for - g.points_against) DESC, d.team_name
LIMIT 5
""").show(truncate=False)
