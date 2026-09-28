"""Databricks Python task. Parameters: blob_path, raw_container, storage_account.

Reads an Airflow-landed JSONL snapshot and records each distinct match version.
The Gold models select the latest version, so old player/event rows remain auditable.
"""

from pyspark.sql import functions as F
from delta.tables import DeltaTable

blob_path = dbutils.widgets.get("blob_path")  # noqa: F821 - Databricks injects dbutils
container = dbutils.widgets.get("raw_container")  # noqa: F821
account = dbutils.widgets.get("storage_account")  # noqa: F821
catalog = dbutils.widgets.get("catalog")  # noqa: F821
schema = dbutils.widgets.get("schema")  # noqa: F821

spark.sql(f"CREATE SCHEMA IF NOT EXISTS `{catalog}`.`{schema}`")  # noqa: F821
source = spark.read.json(  # noqa: F821
    f"abfss://{container}@{account}.dfs.core.windows.net/{blob_path}"
).withColumn("ingested_at", F.current_timestamp())

if source.select("match.match_id").distinct().count() != source.count():
    raise ValueError("Duplicate fixture key in landed snapshot")


def append_new_versions(frame, table_name, key_columns):
    full_name = f"`{catalog}`.`{schema}`.`{table_name}`"
    frame = frame.dropDuplicates(key_columns)
    if not spark.catalog.tableExists(f"{catalog}.{schema}.{table_name}"):  # noqa: F821
        frame.write.format("delta").mode("overwrite").saveAsTable(full_name)
        return
    condition = " AND ".join(f"target.`{key}` = source.`{key}`" for key in key_columns)
    DeltaTable.forName(spark, full_name).alias("target").merge(  # noqa: F821
        frame.alias("source"), condition
    ).whenNotMatchedInsertAll().execute()


bronze = source.select(
    F.col("match.match_id").alias("match_id"),
    F.col("match.source_hash").alias("source_hash"),
    "ingested_at",
    F.to_json("raw").alias("raw_json"),
)
append_new_versions(bronze, "bronze_match_versions", ["match_id", "source_hash"])

matches = source.select("match.*", "ingested_at").drop("players", "scoring_events")

players = source.select(
    F.col("match.match_id").alias("match_id"),
    F.col("match.source_hash").alias("source_hash"),
    F.col("match.transform_version").alias("transform_version"),
    "ingested_at", F.explode_outer("match.players").alias("player_record"),
).where(F.col("player_record").isNotNull()).select(
    "match_id", "source_hash", "transform_version", "ingested_at", "player_record.*"
)
append_new_versions(players, "silver_player_versions", ["match_id", "source_hash", "transform_version", "side", "jersey"])

events = source.select(
    F.col("match.match_id").alias("match_id"),
    F.col("match.source_hash").alias("source_hash"),
    F.col("match.transform_version").alias("transform_version"),
    "ingested_at", F.explode_outer("match.scoring_events").alias("event_record"),
).where(F.col("event_record").isNotNull()).select(
    "match_id", "source_hash", "transform_version", "ingested_at", "event_record.*"
)
append_new_versions(events, "silver_scoring_versions", ["match_id", "source_hash", "transform_version", "event_id"])

# Commit the match version last: Gold only sees versions whose child rows loaded.
append_new_versions(matches, "silver_match_versions", ["match_id", "source_hash", "transform_version"])

