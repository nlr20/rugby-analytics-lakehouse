# dbt on Databricks Free Edition

dbt reads the current season-snapshot Silver tables in `workspace.rugby_analytics` and builds views and marts in `workspace.rugby_dbt`. On 29 September 2026, the expanded five-season build completed **seven models and 31 passing data tests** with no warnings or errors. A separate count query confirmed 755 fixtures, 688 match facts, 67 without a source result and 1,376 team appearances. The earlier 2024–25-only build had five models and 22 passing tests.

After [the five-season Databricks ingestion](../free-edition/README.md), set your SQL warehouse connection values and run from this directory:

```powershell
$env:DATABRICKS_HOST='your-workspace-hostname'
$env:DATABRICKS_HTTP_PATH='/sql/1.0/warehouses/your-warehouse-id'
dbt debug --profiles-dir .
dbt build --profiles-dir .
```

The committed [profile](profiles.yml) uses browser OAuth and contains no token. `stg_current_fixtures` selects the latest published snapshot for each season. `stg_latest_matches` keeps only completed fixture versions. Team and match marts, player scoring, and fixture schedule follow. Tests check keys, team relationships, match versus team points, and fixture status reconciliation. One 2022–23 match lacks published scoring events; the score-event exception is surfaced by the ingestion and local audit instead of being treated as a complete event history.

See Databricks' [dbt Core connection guide](https://docs.databricks.com/aws/en/partners/prep/dbt) for OAuth and SQL warehouse details. The Free Edition warehouse has usage quotas.
