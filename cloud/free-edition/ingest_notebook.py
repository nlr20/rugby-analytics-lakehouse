# Databricks notebook source
"""Ingest one season snapshot from a managed Volume into versioned Delta tables."""

from datetime import datetime, timezone
import re

from delta.tables import DeltaTable
from pyspark.sql import Window, functions as F

dbutils.widgets.text("catalog", "workspace")
dbutils.widgets.text("schema", "rugby_analytics")
dbutils.widgets.text("landing_path", "/Volumes/workspace/rugby_analytics/landing/urc-2024-25-v3-47ce925d0db9.jsonl")
catalog = dbutils.widgets.get("catalog")
schema = dbutils.widgets.get("schema")
landing_path = dbutils.widgets.get("landing_path")
for name in (catalog, schema):
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
        raise ValueError(f"Invalid catalog or schema name: {name!r}")
if not landing_path.startswith(f"/Volumes/{catalog}/{schema}/"):
    raise ValueError("landing_path must be inside the selected catalog and schema")

namespace = f"`{catalog}`.`{schema}`"
run_at = datetime.now(timezone.utc).isoformat()
source = spark.read.json(landing_path).withColumn("ingested_at", F.lit(run_at).cast("timestamp"))  # noqa: F821
source_count = source.count()
if not source_count:
    raise ValueError("Landing file has no fixtures")
if source.where(F.col("match.match_id").isNull() | F.col("source_snapshot_hash").isNull()).limit(1).count():
    raise ValueError("Landing file is missing a match ID or snapshot hash; regenerate it with the multi-season CLI")
if source.select("match.match_id").distinct().count() != source_count:
    raise ValueError("Landing file contains duplicate fixture IDs")
if source.select("match.season", "source_snapshot_hash").distinct().count() != 1:
    raise ValueError("Landing file must contain exactly one season snapshot")
if source.where(~F.col("match.status").isin("completed", "result_unavailable")).limit(1).count():
    raise ValueError("Landing file contains an invalid fixture status")
if source.where((F.col("match.status") == "completed") &
                (F.col("match.home_score").isNull() | F.col("match.away_score").isNull())).limit(1).count():
    raise ValueError("Completed match is missing a score")
if source.where((F.col("match.status") == "result_unavailable") &
                (F.col("match.home_score").isNotNull() | F.col("match.away_score").isNotNull())).limit(1).count():
    raise ValueError("Fixture marked result unavailable has a score")


def append_new_versions(frame, table_name, keys):
    full_name = f"{namespace}.`{table_name}`"
    frame = frame.dropDuplicates(keys)
    if not spark.catalog.tableExists(f"{catalog}.{schema}.{table_name}"):  # noqa: F821
        frame.write.format("delta").mode("append").saveAsTable(full_name)
        return
    condition = " AND ".join(f"target.`{key}` = incoming.`{key}`" for key in keys)
    DeltaTable.forName(spark, full_name).alias("target").merge(  # noqa: F821
        frame.alias("incoming"), condition
    ).whenNotMatchedInsertAll().execute()


match_keys = ["match_id", "source_hash", "transform_version"]
completed = source.where(F.col("match.status") == "completed")
incoming_keys = completed.select(*[F.col(f"match.{key}").alias(key) for key in match_keys])
match_versions_name = f"{catalog}.{schema}.silver_match_versions"
if spark.catalog.tableExists(match_versions_name):  # noqa: F821
    existing_keys = spark.table(match_versions_name).select(*match_keys)  # noqa: F821
    new_match_versions = incoming_keys.join(existing_keys, match_keys, "left_anti").count()
else:
    new_match_versions = completed.count()

bronze = source.select(F.col("match.match_id").alias("match_id"),
                       F.col("match.source_hash").alias("source_hash"),
                       "ingested_at", F.to_json("raw").alias("raw_json"))
append_new_versions(bronze, "bronze_match_versions", ["match_id", "source_hash"])

players = completed.select(*[F.col(f"match.{key}").alias(key) for key in match_keys],
                           "ingested_at", F.explode_outer("match.players").alias("player_record"))
players = players.where(F.col("player_record").isNotNull()).select(
    *match_keys, "ingested_at", "player_record.*")
append_new_versions(players, "silver_player_versions", match_keys + ["side", "jersey"])

events = completed.select(*[F.col(f"match.{key}").alias(key) for key in match_keys],
                          "ingested_at", F.explode_outer("match.scoring_events").alias("event_record"))
events = events.where(F.col("event_record").isNotNull()).select(
    *match_keys, "ingested_at", "event_record.*")
append_new_versions(events, "silver_scoring_versions", match_keys + ["event_id"])

# The original 2024-25 Silver match table has this schema; status lives in fixture snapshots.
matches = completed.select("match.*", "ingested_at").drop(
    "players", "scoring_events", "status", "source_index")
append_new_versions(matches, "silver_match_versions", match_keys)

fixtures = source.select(F.col("match.match_id").alias("match_id"),
                         F.col("match.season").alias("season"),
                         F.col("match.source_index").alias("source_index"),
                         F.col("match.status").alias("status"),
                         F.col("match.played_at").alias("played_at"),
                         F.col("match.round_type").alias("round_type"),
                         F.col("match.round_number").alias("round_number"),
                         F.col("match.home_team").alias("home_team"),
                         F.col("match.away_team").alias("away_team"),
                         F.col("match.home_score").alias("home_score"),
                         F.col("match.away_score").alias("away_score"),
                         F.col("match.source_hash").alias("source_hash"),
                         F.col("match.transform_version").alias("transform_version"),
                         "source_snapshot_hash", "ingested_at")
append_new_versions(fixtures, "silver_fixture_versions",
                    ["season", "source_snapshot_hash", "source_index", "transform_version"])

# Publish the manifest last: readers see only fully loaded season snapshots.
manifest = source.select(F.col("match.season").alias("season"),
                         F.col("match.transform_version").alias("transform_version"),
                         "source_snapshot_hash", "ingested_at").distinct()
append_new_versions(manifest, "silver_season_snapshots", ["season", "source_snapshot_hash", "transform_version"])

current_snapshot = spark.table(f"{catalog}.{schema}.silver_season_snapshots").withColumn(  # noqa: F821
    "rank", F.row_number().over(Window.partitionBy("season").orderBy(
        F.col("ingested_at").desc(), F.col("transform_version").desc(),
        F.col("source_snapshot_hash").desc())))
current_snapshot = current_snapshot.where(F.col("rank") == 1).select(
    "season", "source_snapshot_hash", "transform_version")
current_fixtures = spark.table(f"{catalog}.{schema}.silver_fixture_versions").join(  # noqa: F821
    current_snapshot, ["season", "source_snapshot_hash", "transform_version"])
current_complete = current_fixtures.where(F.col("status") == "completed").select(*match_keys)
latest = spark.table(match_versions_name).join(current_complete, match_keys)  # noqa: F821
current_events = spark.table(f"{catalog}.{schema}.silver_scoring_versions").join(  # noqa: F821
    current_complete, match_keys)
event_totals = current_events.groupBy("match_id").agg(
    F.sum(F.when(F.col("side") == "home", F.col("points")).otherwise(0)).alias("home_event_points"),
    F.sum(F.when(F.col("side") == "away", F.col("points")).otherwise(0)).alias("away_event_points"))
checked = latest.join(event_totals, "match_id", "left").fillna(
    0, subset=["home_event_points", "away_event_points"])
score_discrepancies = checked.where((F.col("home_score") != F.col("home_event_points")) |
                                    (F.col("away_score") != F.col("away_event_points"))).count()
print({"source_fixtures": source_count, "new_match_versions": new_match_versions,
       "current_fixtures": current_fixtures.count(), "current_matches": latest.count(),
       "fixtures_without_result": current_fixtures.where(F.col("status") == "result_unavailable").count(),
       "score_discrepancies": score_discrepancies})
