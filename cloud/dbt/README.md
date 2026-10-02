# dbt on Databricks Free Edition

dbt reads the current season-snapshot Silver tables in `workspace.rugby_analytics` and builds views and marts in `workspace.rugby_dbt`. On 1 October 2026, after the completed 2025–26 and repaired 2022–23 snapshots were ingested, the full five-season build completed **nine models and 46 passing data tests** with no warnings or errors. The refreshed site export confirmed 755 fixtures, 755 match facts, zero without a source result, 1,510 team appearances and 11,951 current scoring events. The earlier 2024–25-only build had five models and 22 passing tests.

After [the five-season Databricks ingestion](../free-edition/README.md), set your SQL warehouse connection values and run from this directory:

```powershell
$env:DATABRICKS_HOST='your-workspace-hostname'
$env:DATABRICKS_HTTP_PATH='/sql/1.0/warehouses/your-warehouse-id'
dbt debug --profiles-dir .
dbt build --profiles-dir .
```

The committed [profile](profiles.yml) uses browser OAuth and contains no token. `stg_current_fixtures` selects the latest published snapshot for each season. `stg_latest_matches` keeps only completed fixture versions. Team and match marts, team-level venue results, player scoring, current scoring events, and fixture schedule follow. Tests check keys, team relationships, match versus team points, team appearances and venue outcomes, and fixture status reconciliation. Across the five seasons, listed scoring events and final scores each total 36,826 points; the prior 56-point gap was resolved by the [2022–23 match repair](../../docs/2022-23-match-repair.md).

The local Airflow container selects the separate `airflow` target with `--target airflow`. That target reads `DATABRICKS_TOKEN` from its ignored `.env` file; the default `free_edition` target remains browser OAuth for manual desktop runs. The Docker image has parsed the project with this target, but a token-authenticated dbt build inside Airflow has not yet run.

See Databricks' [dbt Core connection guide](https://docs.databricks.com/aws/en/partners/prep/dbt) for OAuth and SQL warehouse details. The Free Edition warehouse has usage quotas.
