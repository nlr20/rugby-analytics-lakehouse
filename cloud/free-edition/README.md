# Five-season Databricks Free Edition run

The existing `workspace.rugby_analytics` schema and managed `landing` Volume can be reused. The earlier 2024–25 notebook and dbt runs were verified manually; **this five-season update has not yet run in Databricks**.

## 1. Prepare and upload

From the repository root, run `rugby-lakehouse prepare-landing --all-seasons`. Upload these five ignored local files to the managed Volume using **Catalog > workspace > rugby_analytics > landing > Upload**:

| Season | Landing file under `data/landing/` |
| --- | --- |
| 2021–22 | `urc-2021-22-v3-55a0432d9866.jsonl` |
| 2022–23 | `urc-2022-23-v3-91d91714ea59.jsonl` |
| 2023–24 | `urc-2023-24-v3-a5b542793691.jsonl` |
| 2024–25 | `urc-2024-25-v3-47ce925d0db9.jsonl` |
| 2025–26 | `urc-2025-26-v3-5792a28de763.jsonl` |

These names identify the [audited snapshot](../../docs/multiseason-audit.md). If upstream data changes, `prepare-landing` will print new hashes and filenames. Each file goes to `/Volumes/workspace/rugby_analytics/landing/<filename>`.

## 2. Ingest each season

Update or import [ingest_notebook.py](ingest_notebook.py) in Databricks. Run it on serverless compute once for each of the five paths, setting its `landing_path` widget. Start with 2024–25 so the existing one-season data is migrated to the new fixture-snapshot model; run the other seasons in any order. The run prints source fixtures, new completed match versions, current fixtures, current completed matches, fixtures without a result, and score-event discrepancies.

Expected **after all five files**: 755 current fixtures, 688 current completed matches, 67 fixtures without results, and one score-event discrepancy. Re-running the same file should show zero new match versions. The 2022–23 discrepancy is documented in the audit; investigate any additional discrepancy before using the marts.

The notebook writes append-only Bronze raw versions, append-only completed match and player versions, versioned fixture rows, and a season snapshot manifest. The manifest is published after its rows so current-state readers use only a complete season snapshot. Previous 2024–25 Delta data remains in its version tables; a new `transform_version` is added for the five-season design.

## 3. Build Gold and dbt

Update or import [gold_notebook.py](gold_notebook.py), then run it once. It creates `gold_fixture_schedule`, `dim_team`, `fact_match`, `gold_team_season` and `gold_player_scoring` as managed Delta tables and checks row and point reconciliation. Expected totals after all seasons: 755 fixtures, 67 without a result, 688 match facts and 1,376 team appearances. The previous 2024–25 Gold run alone was verified at 151 facts, 16 teams and 7,313 match points; the five-season totals are not yet verified in Databricks.

Then run `dbt build --profiles-dir .` in [cloud/dbt](../dbt/README.md). The dbt project reads current Silver snapshots and builds an independent set of analytical tables and tests. Lastly, refresh the [dashboard datasets](../dashboard/README.md) or connect [Power BI Desktop](../powerbi/README.md).

Databricks [managed Volume files](https://docs.databricks.com/aws/en/volumes/volume-files) and [Free Edition limits](https://docs.databricks.com/aws/en/getting-started/free-edition-limitations) are documented by Databricks. Free Edition has quotas, so a five-season backfill may need to be split across days.
