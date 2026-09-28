"""Manual Airflow backfill: source JSON -> managed Volume -> Delta notebooks -> dbt."""

from datetime import datetime, timedelta, timezone
import os
from pathlib import Path
import subprocess

from airflow.decorators import dag, task
from airflow.models import Variable
from airflow.providers.databricks.operators.databricks import DatabricksRunNowOperator
from databricks.sdk import WorkspaceClient

from rugby_lakehouse.landing import write_landing_file
from rugby_lakehouse.source import SEASONS, read_matches


@dag(
    dag_id="rugby_urc_five_seasons",
    start_date=datetime(2026, 1, 1, tzinfo=timezone.utc),
    schedule=None,
    catchup=False,
    max_active_runs=1,
    default_args={"retries": 2, "retry_delay": timedelta(minutes=10)},
    tags=["rugby", "lakehouse", "backfill"],
)
def rugby_urc_pipeline():
    @task
    def prepare_and_upload(season: str) -> str:
        matches = read_matches(season=season)
        landing = write_landing_file(matches, Path(os.environ["RUGBY_LANDING_DIR"]), season)
        local_file = Path(landing["landing_file"])
        remote_file = f"/Volumes/workspace/rugby_analytics/landing/{local_file.name}"
        WorkspaceClient().files.upload_from(remote_file, str(local_file), overwrite=True)
        return remote_file

    @task
    def build_dbt() -> None:
        project = Path(os.environ["RUGBY_REPO_DIR"]) / "cloud" / "dbt"
        subprocess.run(["dbt", "build", "--profiles-dir", str(project),
                        "--project-dir", str(project)], check=True)

    previous = None
    for season in SEASONS:
        label = season.replace("-", "_")
        uploaded = prepare_and_upload.override(task_id=f"upload_{label}")(season)
        ingested = DatabricksRunNowOperator(
            task_id=f"ingest_{label}",
            databricks_conn_id="databricks_default",
            job_id=int(Variable.get("rugby_ingest_job_id", default_var="0")),
            notebook_params={"landing_path": "{{ ti.xcom_pull(task_ids='upload_" + label + "') }}"},
            wait_for_termination=True,
        )
        if previous is not None:
            previous >> uploaded
        uploaded >> ingested
        previous = ingested

    gold = DatabricksRunNowOperator(
        task_id="build_gold",
        databricks_conn_id="databricks_default",
        job_id=int(Variable.get("rugby_gold_job_id", default_var="0")),
        wait_for_termination=True,
    )
    previous >> gold >> build_dbt()


rugby_urc_pipeline()

