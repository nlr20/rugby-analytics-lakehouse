"""Local season JSON -> managed Volume -> PySpark Silver -> dbt Gold."""

from datetime import datetime, timedelta, timezone
import os
from pathlib import Path
import subprocess

from airflow.sdk import dag, task
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
    def ingest_landing_folder() -> None:
        job_id = int(os.environ["RUGBY_INGEST_JOB_ID"])
        run = WorkspaceClient().jobs.run_now_and_wait(job_id, timeout=timedelta(minutes=45))
        print(f"Databricks ingestion job {job_id} completed: run {run.run_id}")

    @task
    def build_dbt() -> None:
        project = Path(os.environ["RUGBY_REPO_DIR"]) / "cloud" / "dbt"
        subprocess.run(["dbt", "build", "--profiles-dir", str(project),
                        "--project-dir", str(project), "--target", "airflow"], check=True)

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

    previous >> ingest_landing_folder() >> build_dbt()


rugby_urc_pipeline()

