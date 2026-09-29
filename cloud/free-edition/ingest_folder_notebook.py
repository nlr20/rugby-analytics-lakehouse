# Databricks notebook source
"""Process new season snapshots from the managed landing Volume in one run."""

import re

from pyspark.sql import Window, functions as F


dbutils.widgets.text("catalog", "workspace")
dbutils.widgets.text("schema", "rugby_analytics")
catalog = dbutils.widgets.get("catalog")
schema = dbutils.widgets.get("schema")
for name in (catalog, schema):
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
        raise ValueError(f"Invalid catalog or schema name: {name!r}")

landing_dir = f"/Volumes/{catalog}/{schema}/landing/"
manifest_name = f"{catalog}.{schema}.silver_season_snapshots"
known = set()
if spark.catalog.tableExists(manifest_name):
    known = {tuple(row) for row in spark.table(manifest_name).select(
        "season", "source_snapshot_hash", "transform_version").collect()}

# The old 2024-25 upload has no transform version in its name and is ignored.
# A stable name such as urc-2026-27.jsonl also works when overwritten weekly.
pattern = re.compile(r"urc-(20\d{2}-\d{2})(?:-v3-[0-9a-f]{12})?\.jsonl$")
files = [item for item in dbutils.fs.ls(landing_dir) if pattern.fullmatch(item.name)]
files.sort(key=lambda item: (getattr(item, "modificationTime", 0), item.name))

processed = []
skipped = []
for item in files:
    path = landing_dir + item.name
    frame = spark.read.json(path)
    if "source_snapshot_hash" not in frame.columns:
        raise ValueError(f"Landing file lacks source_snapshot_hash: {path}")
    metadata = frame.select(
        F.col("match.season").alias("season"), "source_snapshot_hash",
        F.col("match.transform_version").alias("transform_version")
    ).distinct().collect()
    if len(metadata) != 1:
        raise ValueError(f"Expected one season and snapshot hash in {path}")
    row = metadata[0]
    key = (row.season, row.source_snapshot_hash, row.transform_version)
    if row.season != pattern.fullmatch(item.name).group(1):
        raise ValueError(f"Season in file does not match filename: {path}")
    if row.transform_version != 3:
        raise ValueError(f"Landing file needs transform version 3: {path}")
    if key in known:
        skipped.append(item.name)
        continue
    dbutils.notebook.run("./ingest_notebook", 0, {
        "catalog": catalog, "schema": schema, "landing_path": path,
    })
    known.add(key)
    processed.append(item.name)

if not spark.catalog.tableExists(manifest_name):
    raise ValueError("No season snapshots were ingested")

current_snapshots = spark.table(manifest_name).withColumn(
    "version_rank", F.row_number().over(Window.partitionBy("season").orderBy(
        F.col("ingested_at").desc(), F.col("transform_version").desc(),
        F.col("source_snapshot_hash").desc()))
).where(F.col("version_rank") == 1).select("season", "source_snapshot_hash", "transform_version")
current = spark.table(f"{catalog}.{schema}.silver_fixture_versions").join(
    current_snapshots, ["season", "source_snapshot_hash", "transform_version"])
counts = current.groupBy("season", "status").count().orderBy("season", "status").collect()
match_keys = ["match_id", "source_hash", "transform_version"]
complete = current.where(F.col("status") == "completed").select(*match_keys)
matches = spark.table(f"{catalog}.{schema}.silver_match_versions").join(complete, match_keys)
events = spark.table(f"{catalog}.{schema}.silver_scoring_versions").join(complete, match_keys)
points = events.groupBy("match_id").agg(
    F.sum(F.when(F.col("side") == "home", F.col("points")).otherwise(0)).alias("home_points"),
    F.sum(F.when(F.col("side") == "away", F.col("points")).otherwise(0)).alias("away_points"))
checked = matches.join(points, "match_id", "left").fillna(0, subset=["home_points", "away_points"])
discrepancies = checked.where((F.col("home_score") != F.col("home_points")) |
                              (F.col("away_score") != F.col("away_points"))).count()
print({"processed": processed, "already_loaded": skipped,
       "current_fixtures": current.count(), "current_matches": matches.count(),
       "score_discrepancies": discrepancies,
       "current_fixtures_by_season_and_status": [row.asDict() for row in counts]})
