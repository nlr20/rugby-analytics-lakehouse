# Cloud path and deployment state

The working target is the existing AWS-hosted Databricks Free Edition workspace. Its managed `landing` Volume is the cloud storage stage; a serverless PySpark notebook creates Bronze and Silver Delta tables. Local dbt Core owns Gold in `workspace.rugby_dbt`, and the SQL datasets support a Databricks dashboard or Power BI Desktop.

| Part | State |
| --- | --- |
| 2024–25 Volume ingestion, Delta Gold, dbt and dashboard | Manually run and verified earlier |
| Five-season local Python pipeline | Run and checked; see [audit](../docs/multiseason-audit.md) |
| Five-season Silver notebook and folder runner | Manually run: 755 fixtures and 755 results after the 2025–26 backfill |
| Five-season dbt Gold | Built: nine models and 46 passing tests; Gold counts reconciled |
| Five-season dashboard SQL | Nine queries verified; existing workspace views are being configured manually, and the new close-game details view is ready to add |
| [Airflow DAG](airflow/rugby_urc.py) | Local Docker Airflow starts and registers the paused DAG; Databricks task chain not run end to end |
| [Azure ADLS reader](databricks/ingest.py) | Separate draft; incompatible with this AWS-hosted Free Edition path as written |
| Power BI report | [Connection and model plan](powerbi/README.md) prepared; no `.pbix` claimed |

The [manual Free Edition guide](free-edition/README.md) records the verified run. The Airflow DAG reads JSON files from `RUGBY_SOURCE_DIR` (default: `RUGBY_REPO_DIR/data/source`), writes content-hashed JSONL, uploads it to the managed Volume, invokes the folder-ingestion notebook once, then runs dbt Core. For 2022–23 it **requires** `celtic-2022-2023-repaired.json`; for 2025–26 it **requires** `celtic-2025-2026-api.json`. It will not silently use the older incomplete copies. Other seasons use `celtic-YYYY-YYYY.json`; a new season such as `2026-27` can use that name without a code edit. The Airflow worker must be able to read these ignored local files. By default the DAG is manual-triggered to avoid unexpected serverless quota use; `RUGBY_AIRFLOW_SCHEDULE` can set a schedule after deployment. `RUGBY_SEASONS` selects the seasons to process. The older Gold notebook stays as a comparison implementation; the pipeline does not call it.

The [local Airflow setup](airflow/README.md) includes a Docker image with the Databricks SDK and dbt Core. Its worker mounts this repository, so ignored source JSON remains local. The SDK uploads to the Volume and triggers a single-notebook Databricks job, then dbt builds Gold with a token-based profile. The job must run [ingest_folder_notebook.py](free-edition/ingest_folder_notebook.py) on serverless compute, with [ingest_notebook.py](free-edition/ingest_notebook.py) in the same workspace folder. Store credentials in ignored local `.env`, not Git. The DAG has not completed an Airflow run yet. Power BI is deferred; the existing Databricks dashboard remains the reporting view.
