# Five-season Databricks Free Edition run

The existing `workspace.rugby_analytics` schema and managed `landing` Volume were reused. On 29 September 2026, the five-season folder ingestion and dbt Gold build were verified in Databricks Free Edition.

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

## 2. Ingest the landing folder

Import [ingest_notebook.py](ingest_notebook.py) and [ingest_folder_notebook.py](ingest_folder_notebook.py) into the **same Databricks workspace folder**. Run the folder notebook on serverless compute. It finds all `v3` JSONL files in the managed `landing` Volume, reads the season and snapshot hash inside each, skips snapshots already recorded in the Delta manifest, and calls the ingestion notebook for the rest. It ignores the old 2024–25 JSONL filename. The output lists processed and already-loaded filenames, current fixture and match totals, score-event discrepancies, and counts by season/status.

The previously ingested 2024–25 `v3` file should be reported as already loaded. The other four files should be processed in one run. A second run with no changed input should process nothing. If a weekly source update changes a match, `prepare-landing --season YYYY-YY` creates a new content-hashed filename; upload it and rerun the folder notebook. An overwritten stable filename such as `urc-2026-27.jsonl` also works if its internal snapshot hash is regenerated when the content changes. Do not manually edit that hash.

**Observed after all five files:** 755 current fixtures, 688 current completed matches, 67 fixtures without results, and one score-event discrepancy. The 2022–23 discrepancy is documented in the audit; investigate any additional discrepancy before using the marts.

The notebook writes append-only Bronze raw versions, append-only completed match and player versions, versioned fixture rows, and a season snapshot manifest. The manifest is published after its rows so current-state readers use only a complete season snapshot. Previous 2024–25 Delta data remains in its version tables; a new `transform_version` is added for the five-season design.

## 3. Build dbt Gold

Run `dbt build --profiles-dir .` in [cloud/dbt](../dbt/README.md). dbt reads current Silver snapshots and builds the Gold analytical tables and tests. The 29 September build completed seven models and 31 passing data tests. A read-only count check found 755 fixtures, 67 without a result, 688 match facts and 1,376 team appearances. The [Gold notebook](gold_notebook.py) is retained as a comparison implementation and is not required for the main pipeline. Lastly, refresh the [dashboard datasets](../dashboard/README.md) or connect [Power BI Desktop](../powerbi/README.md).

Databricks [managed Volume files](https://docs.databricks.com/aws/en/volumes/volume-files) and [Free Edition limits](https://docs.databricks.com/aws/en/getting-started/free-edition-limitations) are documented by Databricks. Free Edition has quotas, so a five-season backfill may need to be split across days.
