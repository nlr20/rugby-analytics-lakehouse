# dbt on Databricks Free Edition

These models read the versioned Silver tables in `workspace.rugby_analytics` and build a separate `workspace.rugby_dbt` schema. Keeping them separate lets the dbt output be compared with the verified Gold notebook tables. The dbt path has not yet been run against the workspace.

The committed [`profiles.yml`](profiles.yml) contains no credentials. It uses OAuth browser sign-in, the workspace hostname, and the SQL warehouse HTTP path. Find both values under **SQL Warehouses > Serverless Starter Warehouse > Connection Details**. The hostname should not include `https://`; the HTTP path begins `/sql/1.0/warehouses/`. Do not commit a token or paste one into an issue.

From this directory in PowerShell:

```powershell
python -m pip install dbt-databricks
$env:DATABRICKS_HOST='your-workspace-hostname'
$env:DATABRICKS_HTTP_PATH='/sql/1.0/warehouses/your-warehouse-id'
dbt debug --profiles-dir .
dbt build --profiles-dir .
```

`dbt build` creates the match and team models, then runs key, relationship, and reconciliation tests. The reconciliation test checks that every match contributes two team appearances and that team points equal the match score total. The SQL warehouse uses the Free Edition daily quota; pause if the account reaches its limit.

See Databricks' [dbt Core connection guide](https://docs.databricks.com/aws/en/partners/prep/dbt) for OAuth and warehouse connection details.
