# Cloud deployment draft

The Airflow DAG, Databricks job script, and dbt models are implementation code for the planned Azure path. They are not yet deployed or integration tested against an Azure/Databricks workspace.

For the no-cost path using the available AWS-hosted Databricks Free Edition workspace, see [Free Edition setup](free-edition/README.md) and [dbt setup](dbt/README.md). Bronze, Silver, and Gold notebook runs have been verified there, and the dbt build passed all 22 data tests. The Azure `abfss://` reader below is not suitable for that workspace.

## Required configuration

| Component | Configuration |
| --- | --- |
| Airflow worker | Install this Python package, `azure-storage-blob`, and the Databricks Airflow provider. Set `AZURE_STORAGE_CONNECTION_STRING` and `RUGBY_RAW_CONTAINER` in secret-backed environment configuration. |
| Airflow connection | Create `databricks_default` and Variable `rugby_databricks_job_id`. |
| Databricks job | Python task `cloud/databricks/ingest.py`; parameters `blob_path`, `raw_container`, `storage_account`, `catalog`, `schema`. Airflow passes `blob_path`. Configure the remaining parameters in the job. |
| Databricks storage | Grant the job identity read access to the raw ADLS container, and write access to its Unity Catalog schema. |
| dbt | Use `dbt-databricks`, a Databricks profile named `rugby_analytics`, and environment variables `RUGBY_DATABRICKS_CATALOG` and `RUGBY_DATABRICKS_SCHEMA`. Run `dbt build` after the Databricks ingestion job. |

The DAG currently triggers ingestion, but dbt is a separate deployment step. Before production use, add a dbt task after ingestion and verify credentials, Delta schemas, source corrections, and reruns in a real workspace.

