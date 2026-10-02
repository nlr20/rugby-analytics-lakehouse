FROM apache/airflow:3.3.2-python3.11

# dbt and the SDK run in the same local Airflow worker; no project data is baked in.
RUN pip install --no-cache-dir "databricks-sdk==0.117.0" "dbt-databricks==1.12.5"
