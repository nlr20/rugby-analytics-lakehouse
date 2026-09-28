"""Airflow DAG for the URC snapshot. Install this package on Airflow workers."""

from datetime import datetime, timedelta, timezone
import os

from airflow.decorators import dag, task
from airflow.models import Variable
from airflow.providers.databricks.operators.databricks import DatabricksRunNowOperator
from azure.storage.blob import BlobServiceClient

from rugby_lakehouse.source import read_matches
from rugby_lakehouse.transform import canonical_json, normalize_match


@dag(
    dag_id="rugby_urc_2024_25",
    start_date=datetime(2024, 9, 1, tzinfo=timezone.utc),
    schedule="0 6 * * *",
    catchup=False,
    max_active_runs=1,
    default_args={"retries": 2, "retry_delay": timedelta(minutes=10)},
    tags=["rugby", "lakehouse"],
)
def rugby_urc_pipeline():
    @task
    def land_snapshot(logical_date: str) -> str:
        matches = read_matches()
        normalized = [normalize_match(match) for match in matches]
        if len({m["match_id"] for m in normalized}) != len(matches):
            raise ValueError("Duplicate fixture identity in source snapshot")
        path = f"rugby/urc-2024-25/{logical_date}/matches.jsonl"
        body = "\n".join(
            canonical_json({"raw": raw, "match": match})
            for raw, match in zip(matches, normalized)
        ) + "\n"
        client = BlobServiceClient.from_connection_string(
            os.environ["AZURE_STORAGE_CONNECTION_STRING"]
        )
        client.get_blob_client(
            container=os.environ["RUGBY_RAW_CONTAINER"], blob=path
        ).upload_blob(body, overwrite=True)
        return path

    blob_path = land_snapshot("{{ ds }}")
    DatabricksRunNowOperator(
        task_id="build_delta_layers",
        databricks_conn_id="databricks_default",
        job_id=int(Variable.get("rugby_databricks_job_id")),
        notebook_params={"blob_path": blob_path},
    )


rugby_urc_pipeline()

