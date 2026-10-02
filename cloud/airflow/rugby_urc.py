"""Local season JSON -> managed Volume -> PySpark Silver -> dbt Gold."""

from datetime import datetime, timedelta, timezone
import os
from pathlib import Path
import subprocess

from airflow.decorators import dag, task
from airflow.models import Variable
from airflow.providers.databricks.operators.databricks import DatabricksRunNowOperator
from databricks.sdk import WorkspaceClient

from rugby_lakehouse.landing import write_landing_file
from rugby_lakehouse.pipeline_sources import selected_source_path, upload_landing_file
from rugby_lakehouse.source import SEASONS, read_matches, source_file


@dag(
    dag_id="rugby_urc_pipeline",
    start_date=datetime(2026, 1, 1, tzinfo=timezone.utc),
    schedule=os.environ.get("RUGBY_AIRFLOW_SCHEDULE") or None,
    catchup=False,
    max_active_runs=1,
    default_args={"retries": 2, "retry_delay": timedelta(minutes=10)},
    tags=["rugby", "lakehouse", "backfill"],
)
def rugby_urc_pipeline():
    @task
    def prepare_and_upload(season: str) -> str:
        repo = Path(os.environ["RUGBY_REPO_DIR"])
        source_dir = Path(os.environ.get("RUGBY_SOURCE_DIR", repo / "data" / "source"))
        source_path = selected_source_path(source_dir, season)
        matches = read_matches(path=source_path, season=season)
        if not matches:
            raise ValueError(f"Selected source has no fixtures: {source_path}")
        landing = write_landing_file(matches, Path(os.environ["RUGBY_LANDING_DIR"]), season)
        local_file = Path(landing["landing_file"])
        remote_file = f"/Volumes/workspace/rugby_analytics/landing/{local_file.name}"
        upload_landing_file(WorkspaceClient(), local_file, remote_file)
        print(f"{season}: {source_path.name} -> {remote_file} ({landing['matches']} fixtures)")
        return remote_file

    @task
    def build_dbt() -> None:
        project = Path(os.environ["RUGBY_REPO_DIR"]) / "cloud" / "dbt"
        subprocess.run(["dbt", "build", "--profiles-dir", str(project),
                        "--project-dir", str(project)], check=True)

    seasons = [value.strip() for value in os.environ.get(
        "RUGBY_SEASONS", ",".join(SEASONS)).split(",") if value.strip()]
    if not seasons:
        raise ValueError("RUGBY_SEASONS must contain at least one season")
    for season in seasons:
        source_file(season)
    previous = None
    for season in seasons:
        label = season.replace("-", "_")
        uploaded = prepare_and_upload.override(task_id=f"upload_{label}")(season)
        if previous is not None:
            previous >> uploaded
        previous = uploaded

    ingested = DatabricksRunNowOperator(
        task_id="ingest_landing_folder",
        databricks_conn_id="databricks_default",
        job_id=int(Variable.get("rugby_ingest_job_id", default_var="0")),
        wait_for_termination=True,
    )
    previous >> ingested >> build_dbt()


rugby_urc_pipeline()

