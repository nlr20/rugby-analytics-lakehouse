# Cloud path and deployment state

The working target is the existing AWS-hosted Databricks Free Edition workspace. Its managed `landing` Volume is the cloud storage stage; serverless notebooks create Bronze, Silver and Gold Delta tables. Local dbt Core builds a second analytical model in `workspace.rugby_dbt`, and the SQL datasets support a Databricks dashboard or Power BI Desktop.

| Part | State |
| --- | --- |
| 2024–25 Volume ingestion, Delta Gold, dbt and dashboard | Manually run and verified earlier |
| Five-season local Python pipeline | Run and checked; see [audit](../docs/multiseason-audit.md) |
| Five-season Databricks notebooks, dbt models and dashboard SQL | Prepared; manual workspace run pending |
| [Airflow DAG](airflow/rugby_urc.py) | Prepared; not deployed or integration tested |
| [Azure ADLS reader](databricks/ingest.py) | Separate draft; incompatible with this AWS-hosted Free Edition path as written |
| Power BI report | [Connection and model plan](powerbi/README.md) prepared; no `.pbix` claimed |

The [manual Free Edition guide](free-edition/README.md) is the next runbook. Airflow orchestration is a later validation step after the data model is confirmed in the workspace. Its DAG uses the same source reader and landing writer, uploads to the managed Volume, invokes an ingestion notebook job for each season, invokes a Gold notebook job, then runs dbt Core. It is manual-triggered to avoid unexpected serverless quota use.

Airflow needs the repository package, `apache-airflow-providers-databricks`, `databricks-sdk` and dbt Core available to its worker; `RUGBY_LANDING_DIR` and `RUGBY_REPO_DIR` paths; Databricks SDK credentials for Volume upload; a `databricks_default` Airflow connection; and Variables `rugby_ingest_job_id` and `rugby_gold_job_id` pointing to single-notebook Databricks jobs. The two jobs must run [ingest_notebook.py](free-edition/ingest_notebook.py) and [gold_notebook.py](free-edition/gold_notebook.py) on serverless compute. Store credentials outside Git. The DAG has only passed Python syntax checks so far.
