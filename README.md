# Rugby Analytics Lakehouse

**Question:** How do fixtures, teams, player scoring and team performance change across five United Rugby Championship seasons?

This is the flagship data engineering project in the portfolio. The local reference pipeline has processed the 2021–22 through 2025–26 `celtic` JSON snapshots. It keeps raw versions, models current fixtures separately from completed results, handles source corrections, and produces team-season metrics. The five-season Databricks Silver ingestion and dbt Gold build have been run and reconciled in the Free Edition workspace. A local Airflow run has now orchestrated one unchanged season snapshot through upload, ingestion and dbt; Power BI reporting remains deferred.

## Architecture

```mermaid
flowchart LR
    A[Five upstream season JSON snapshots] --> B[Airflow validation and landing]
    B --> C[Databricks managed Volume]
    C --> D[PySpark ingestion]
    D --> E[Bronze: raw match versions]
    D --> F[Silver: fixture snapshots, match and player versions]
    F --> G[dbt Gold: facts, dimensions, marts and tests]
    G --> I[Databricks dashboard / Power BI Desktop]
```

The supported no-cost development path uses a Databricks Free Edition managed Volume as cloud storage, serverless Delta tables and dbt Core. PySpark owns Bronze and Silver; dbt owns Gold. The separate Gold notebook is a comparison implementation, not a required pipeline step. The [local Docker Airflow setup](cloud/airflow/README.md) completed one manual run for the unchanged 2025–26 snapshot: upload, Databricks ingestion job and dbt Gold all succeeded. Power BI is deferred. The available Free Edition workspace is on AWS; the older Azure ADLS script under `cloud/databricks/` is an alternative draft, not part of this verified path. See [cloud setup](cloud/README.md).

## Source and scope

- Source: [transientlunatic/Rugby-Data JSON](https://github.com/transientlunatic/Rugby-Data/tree/master/json) for 2021–22 through 2024–25, plus a [direct feed backfill](docs/direct-api-backfill.md) for the completed 2025–26 season. The [five-season audit](docs/multiseason-audit.md) records the earlier community snapshots and their known gaps. No source dataset is committed.
- Each season now has 151 completed matches in the current Databricks snapshot. The community 2025–26 file stopped at 84 results; the direct feed backfill supplied the remaining results and match details.
- Player coverage means lineup appearances and listed scoring events. The source does not support claims about tackles, carries or complete individual performance.
- The source is a snapshot, not a change feed. Each match and each whole-season snapshot has a content hash. Re-reading an identical snapshot creates no new match version. A corrected score or lineup creates a new version; Bronze preserves the older raw record.
- The source does not publish a fixture ID. For named teams, the key uses competition, season, phase, round and teams. `TBC` fixtures use a temporary source-position key; a later named result replaces the placeholder in the current season snapshot.

## Run locally

Requires Python 3.10+. From the repository root:

```bash
python -m pip install -e '.[dev]'
rugby-lakehouse sync --all-seasons
rugby-lakehouse quality
rugby-lakehouse summary --season 2024-25
python -m pytest -q
```

`sync --all-seasons` fetches the five audited community files, including the incomplete 2025–26 file. Use the [direct feed extractor](docs/direct-api-backfill.md) and `--input data/source/celtic-2025-2026-api.json --season 2025-26` to reproduce the complete season. A future consecutive season such as `2026-27` works with `--season 2026-27` when its upstream file exists. Generated data is ignored under `data/`. Re-run `sync`; `changed_matches` should be zero when source contents are unchanged.

Prepare the managed-Volume uploads with `rugby-lakehouse prepare-landing --all-seasons`, or use `--season YYYY-YY` for a weekly update. Each JSONL line contains the unchanged upstream `raw` record and the normalized `match` record. The filename includes season, transform version and a snapshot hash, so a changed upstream file creates a new landing name. The [folder ingestion notebook](cloud/free-edition/ingest_folder_notebook.py) discovers and processes new snapshots without changing a widget for each file. See the [manual Free Edition guide](cloud/free-edition/README.md).

## Model and checks

| Layer | Local tables / cloud equivalents | Purpose |
| --- | --- | --- |
| Bronze | `bronze_event` / `bronze_match_versions` | Raw changed records and source hashes |
| Silver | `silver_fixture`; match, appearance and event tables / Delta version tables and season manifest | Current fixture snapshots and completed match detail |
| Gold | `dim_team`, `fact_match`, `gold_team_season` / dbt marts including `team_match` and `scoring_event` | Team, match and event analytics by season and venue |

Checks cover duplicate keys, status and score consistency, score-event reconciliation, two team appearances per match, fact counts, team points versus match points, and referential integrity in dbt. The initial community 2022–23 source had one scored match with no lineups or scoring events. A [single-match feed repair](docs/2022-23-match-repair.md) now supplies that detail in the current Databricks snapshot. See the [initial audit](docs/multiseason-audit.md).

On 1 October 2026, the folder ingestion in Databricks reported 755 fixtures, 755 completed matches and zero score-event discrepancies after both source repairs. The full dbt build completed nine models and 46 passing tests. Gold has 1,510 team appearances and 11,951 listed scoring events; listed event points reconcile to all 36,826 final-score points. The [dashboard queries](cloud/dashboard/README.md) include close games, scoring patterns and head-to-head views.

For a future public career-site app, a [versioned JSON exporter](docs/site-data-export.md) prepares a local, validated copy of selected Gold results. Generated data is ignored by Git and has not been published.

The community 2025–26 snapshot stopped at January 2026. The [direct feed backfill](docs/direct-api-backfill.md) builds a complete season JSON and landing file from the same underlying rugby feed; the updated snapshot has been ingested into Databricks and included in the current local site export.
