# dbt on Databricks Free Edition

dbt reads the current season-snapshot Silver tables in `workspace.rugby_analytics` and builds views and marts in `workspace.rugby_dbt`. The 2024–25 model was run previously: five models and 22 data tests passed. The expanded five-season model has seven models and additional fixture checks; it parses locally but **has not yet been built against the updated workspace tables**.

After [the five-season Databricks ingestion](../free-edition/README.md), set your SQL warehouse connection values and run from this directory:

```powershell
$env:DATABRICKS_HOST='your-workspace-hostname'
$env:DATABRICKS_HTTP_PATH='/sql/1.0/warehouses/your-warehouse-id'
dbt debug --profiles-dir .
dbt build --profiles-dir .
```

The committed [profile](profiles.yml) uses browser OAuth and contains no token. `stg_current_fixtures` selects the latest published snapshot for each season. `stg_latest_matches` keeps only completed fixture versions. Team and match marts, player scoring, and fixture schedule follow. Tests check keys, team relationships, match versus team points, and fixture status reconciliation. One 2022–23 match lacks published scoring events; the score-event exception is surfaced by the ingestion and local audit instead of being treated as a complete event history.

See Databricks' [dbt Core connection guide](https://docs.databricks.com/aws/en/partners/prep/dbt) for OAuth and SQL warehouse details. The Free Edition warehouse has usage quotas.
