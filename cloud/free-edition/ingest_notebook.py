# Databricks notebook source
"""Load a manually uploaded rugby snapshot into managed Delta tables."""

from datetime import datetime, timezone
import re

from delta.tables import DeltaTable
from pyspark.sql import Window, functions as F


dbutils.widgets.text("catalog", "workspace")
dbutils.widgets.text("schema", "rugby_analytics")
dbutils.widgets.text(
    "landing_path", "/Volumes/workspace/rugby_analytics/landing/matches.jsonl"
)
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
source = spark.read.json(landing_path).withColumn(  # noqa: F821 - Databricks injects spark
    "ingested_at", F.lit(run_at).cast("timestamp")
)
source_count = source.count()
if source_count == 0:
    raise ValueError("Landing file has no matches")
if source.where(F.col("match.match_id").isNull()).limit(1).count():
    raise ValueError("Landing file contains a missing match ID")
if source.select("match.match_id").distinct().count() != source_count:
    raise ValueError("Landing file contains duplicate fixture keys")


def append_new_versions(frame, table_name, keys):
    full_name = f"{namespace}.`{table_name}`"
    frame = frame.dropDuplicates(keys)
    if not spark.catalog.tableExists(f"{catalog}.{schema}.{table_name}"):  # noqa: F821
        frame.write.format("delta").mode("errorifexists").saveAsTable(full_name)
        return
    condition = " AND ".join(f"target.`{key}` = incoming.`{key}`" for key in keys)
    DeltaTable.forName(spark, full_name).alias("target").merge(  # noqa: F821
        frame.alias("incoming"), condition
    ).whenNotMatchedInsertAll().execute()


match_keys = ["match_id", "source_hash", "transform_version"]
match_versions_name = f"{catalog}.{schema}.silver_match_versions"
incoming_keys = source.select(
    F.col("match.match_id").alias("match_id"),
    F.col("match.source_hash").alias("source_hash"),
    F.col("match.transform_version").alias("transform_version"),
)
if spark.catalog.tableExists(match_versions_name):  # noqa: F821
    existing_keys = spark.table(match_versions_name).select(*match_keys)  # noqa: F821
    new_match_versions = incoming_keys.join(existing_keys, match_keys, "left_anti").count()
else:
    new_match_versions = source_count

bronze = source.select(
    F.col("match.match_id").alias("match_id"),
    F.col("match.source_hash").alias("source_hash"),
    "ingested_at",
    F.to_json("raw").alias("raw_json"),
)
append_new_versions(bronze, "bronze_match_versions", ["match_id", "source_hash"])

players = source.select(
    F.col("match.match_id").alias("match_id"),
    F.col("match.source_hash").alias("source_hash"),
    F.col("match.transform_version").alias("transform_version"),
    "ingested_at",
    F.explode_outer("match.players").alias("player_record"),
).where(F.col("player_record").isNotNull()).select(
    "match_id", "source_hash", "transform_version", "ingested_at", "player_record.*"
)
append_new_versions(
    players, "silver_player_versions", match_keys + ["side", "jersey"]
)

events = source.select(
    F.col("match.match_id").alias("match_id"),
    F.col("match.source_hash").alias("source_hash"),
    F.col("match.transform_version").alias("transform_version"),
    "ingested_at",
    F.explode_outer("match.scoring_events").alias("event_record"),
).where(F.col("event_record").isNotNull()).select(
    "match_id", "source_hash", "transform_version", "ingested_at", "event_record.*"
)
append_new_versions(events, "silver_scoring_versions", match_keys + ["event_id"])

# Publish the match version after its child records are available.
matches = source.select("match.*", "ingested_at").drop("players", "scoring_events")
append_new_versions(matches, "silver_match_versions", match_keys)

latest = spark.table(match_versions_name).withColumn(  # noqa: F821
    "rank", F.row_number().over(
        Window.partitionBy("match_id").orderBy(
            F.col("ingested_at").desc(),
            F.col("transform_version").desc(),
            F.col("source_hash").desc(),
        )
    )
).where(F.col("rank") == 1)
current_events = spark.table(  # noqa: F821
    f"{catalog}.{schema}.silver_scoring_versions"
).join(latest.select(*match_keys), match_keys)
event_totals = current_events.groupBy("match_id").agg(
    F.sum(F.when(F.col("side") == "home", F.col("points")).otherwise(0)).alias("home_event_points"),
    F.sum(F.when(F.col("side") == "away", F.col("points")).otherwise(0)).alias("away_event_points"),
)
checked = latest.join(event_totals, "match_id", "left").fillna(
    0, subset=["home_event_points", "away_event_points"]
)
score_discrepancies = checked.where(
    (F.col("home_score") != F.col("home_event_points"))
    | (F.col("away_score") != F.col("away_event_points"))
).count()

print({
    "source_matches": source_count,
    "new_match_versions": new_match_versions,
    "current_matches": latest.count(),
    "score_discrepancies": score_discrepancies,
})
