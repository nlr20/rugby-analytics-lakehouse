# Cloud path and deployment state

The working target is the existing AWS-hosted Databricks Free Edition workspace. Its managed `landing` Volume is the cloud storage stage; a serverless PySpark notebook creates Bronze and Silver Delta tables. Local dbt Core owns Gold in `workspace.rugby_dbt`, and the SQL datasets support a Databricks dashboard or Power BI Desktop.

| Part | State |
| --- | --- |
| 2024–25 Volume ingestion, Delta Gold, dbt and dashboard | Manually run and verified earlier |
| Five-season local Python pipeline | Run and checked; see [audit](../docs/multiseason-audit.md) |
| Five-season Silver notebook, folder runner, dbt Gold models and dashboard SQL | Prepared; folder runner workspace validation pending |
| [Airflow DAG](airflow/rugby_urc.py) | Prepared; not deployed or integration tested |
| [Azure ADLS reader](databricks/ingest.py) | Separate draft; incompatible with this AWS-hosted Free Edition path as written |
| Power BI report | [Connection and model plan](powerbi/README.md) prepared; no `.pbix` claimed |

The [manual Free Edition guide](free-edition/README.md) is the next runbook. Airflow orchestration is a later validation step after the data model is confirmed in the workspace. Its DAG uses the same source reader and landing writer, uploads new content-hashed JSONL files to the managed Volume, invokes the folder-ingestion notebook once, then runs dbt Core. By default it is manual-triggered to avoid unexpected serverless quota use; `RUGBY_AIRFLOW_SCHEDULE` can set a weekly schedule after deployment. `RUGBY_SEASONS` can select the active season, for example `2026-27`, without changing code. The older Gold notebook stays as a comparison implementation; the pipeline does not call it.

Airflow needs the repository package, `apache-airflow-providers-databricks`, `databricks-sdk` and dbt Core available to its worker; `RUGBY_LANDING_DIR` and `RUGBY_REPO_DIR` paths; Databricks SDK credentials for Volume upload; a `databricks_default` Airflow connection; and Variable `rugby_ingest_job_id` pointing to a single-notebook Databricks job. That job must run [ingest_folder_notebook.py](free-edition/ingest_folder_notebook.py) on serverless compute, with [ingest_notebook.py](free-edition/ingest_notebook.py) in the same workspace folder. Store credentials outside Git. The DAG has only passed Python syntax checks so far.
