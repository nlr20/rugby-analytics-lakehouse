# Local Airflow run

This is a **local development** Airflow instance in Docker. It mounts the repository at `/opt/rugby` and reads the ignored JSON files under `data/source`. It uploads a content-hashed JSONL file to the existing Databricks managed Volume, runs the Databricks folder-ingestion notebook job, then runs dbt Gold. The default DAG is manual-triggered and starts with 2025–26 only; set `RUGBY_SEASONS` in `.env` to a comma-separated list for a wider backfill.

## What a run does

1. **`upload_2025_26` (Airflow container):** With the default `RUGBY_SEASONS=2025-26`, read the local `data/source/celtic-2025-2026-api.json`, validate and convert its 151 fixtures to a versioned JSONL file, then upload that file to `/Volumes/workspace/rugby_analytics/landing/`. Add another season to `RUGBY_SEASONS` to create a separate upload task for it. Each run reads the selected local file again; updated contents produce a different snapshot hash and landing filename.
2. **`ingest_landing_folder` (Databricks job):** Airflow starts job `RUGBY_INGEST_JOB_ID` and waits for it. The job's folder notebook scans **all** matching JSONL files already in the landing Volume, not just the file uploaded by this run. It checks each file's internal season and snapshot hash against `silver_season_snapshots`, skips snapshots already loaded, and calls `ingest_notebook.py` for each new snapshot. That PySpark notebook writes raw versions to Bronze and current fixture, match, player and event versions to Silver Delta tables.
3. **`build_dbt` (Airflow container, SQL on Databricks):** After ingestion succeeds, dbt Core runs inside the local Docker container. Through the Databricks SQL warehouse it builds Gold models from the current Silver tables and runs their data tests. The Databricks Gold notebook is not used by this DAG.

The tasks run in that order; a failure stops the later tasks. Open the DAG run in Airflow and select each task's **Logs** to see the upload choice, Databricks job run ID, and dbt model/test results. The folder notebook's own `processed`/`already_loaded` report is visible in its Databricks job output when that output is available; Airflow currently records the Databricks job result rather than that notebook printout. The DAG has no schedule by default. Re-triggering it with unchanged local JSON uploads the same content-hashed file and should add no new Silver snapshot; dbt still rebuilds and retests Gold.

## One-time setup

1. Start Docker Desktop and wait until the engine is running.
2. In Databricks Workflows, create a job with one serverless notebook task for `ingest_folder_notebook.py`. Keep `ingest_notebook.py` in the same workspace folder. Record the job ID.
3. Create a Databricks credential with permission to write to `/Volumes/workspace/rugby_analytics/landing/`, run that job and use the SQL warehouse. For this local proof, the container uses `DATABRICKS_TOKEN`; use a short-lived token if your workspace allows one. Never paste it into chat or commit it.
4. Copy `.env.example` to `.env` in this directory and fill `DATABRICKS_TOKEN` and `RUGBY_INGEST_JOB_ID`. The repository ignores `.env` files. The workspace host and SQL warehouse path are non-secret values in `compose.yaml`.
5. From the repository root, run `docker compose -f cloud/airflow/compose.yaml up --build -d`. Open `http://localhost:8080`. Airflow standalone generates an admin password inside its state volume; retrieve it with `docker compose -f cloud/airflow/compose.yaml exec airflow cat /opt/airflow/simple_auth_manager_passwords.json.generated`.

Pause the `rugby_urc_pipeline` DAG until both credentials and the Databricks job are configured. Trigger it manually and inspect each task's log. Keep the DAG unscheduled while validating Free Edition quota use.

## First verified run

On 2 October 2026, a manual run of `rugby_urc_pipeline` for `2025-26` completed successfully in local Docker Airflow (run ID `manual__2026-10-02T19:54:11.802574+00:00`). The upload task wrote the existing content-hashed landing file, Databricks job `720051713152873` completed its folder-ingestion notebook, and dbt reported `PASS=55 WARN=0 ERROR=0`: nine models and 46 tests. The Databricks task's notebook output was not returned by the Jobs API, so the skip report was not captured in Airflow. A read-only Silver query after the run found two 2025–26 snapshot versions and the same latest `ingested_at` timestamp (`2026-10-01T17:52:50.267751+00:00`) as the pre-run local export. This confirms the unchanged JSON did not create another season snapshot. A newly changed source snapshot has not yet been exercised through Airflow.

## Local data and authentication

The source selection is explicit: 2022–23 uses `celtic-2022-2023-repaired.json`, 2025–26 uses `celtic-2025-2026-api.json`, and the other seasons use `celtic-YYYY-YYYY.json`. Missing selected files stop the upload task. The local source files, landing JSONL, site export and `.env` are Git-ignored; none are baked into the Docker image.

The default dbt profile remains browser OAuth for manual desktop use. The `airflow` dbt target reads the same `DATABRICKS_TOKEN` from the container environment. If this Free Edition workspace does not offer a suitable non-interactive credential, a live unattended Airflow run is blocked; the manual OAuth path remains available outside Docker. Do not put a browser OAuth refresh token or a personal token in repository files.

This setup uses Airflow's standalone SQLite development mode, not a production deployment. The Airflow state lives in a Docker named volume. The Databricks Volume and Delta tables remain in the workspace.
