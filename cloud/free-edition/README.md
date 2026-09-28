# Databricks Free Edition setup

This is the no-cost development path for the available AWS-hosted Databricks Free Edition workspace. It uses Databricks-managed storage; it does not deploy Azure resources. The Bronze/Silver ingestion and Gold notebook have been manually verified in this workspace.

## Prepare the landing file locally

From the repository root, install the package and run:

```bash
python -m pip install -e '.[dev]'
rugby-lakehouse prepare-landing --source-ref c2de981ddcbcf2362fdc5719eefa6d9172740850
```

This validates the 151-match snapshot, derives match and event fields, and writes a file named `data/landing/urc-2024-25-<snapshot-hash>.jsonl`. For the audited revision, the exact filename is `urc-2024-25-47ce925d0db9.jsonl`. The season distinguishes future seasons; the hash preserves separate snapshots when the same season is corrected. Each line contains both the unchanged upstream `raw` record and a normalized `match` record. The file and all generated data are ignored by Git. To use an already-downloaded snapshot without network access, add `--input path/to/source-snapshot.json`.

The current transform handles **2024–25 only**. Adding another season also requires parameterizing the season in the fixture identity and validating the new source file; the filename convention alone does not add multi-season processing.

## Workspace steps

1. In Catalog Explorer, create the `rugby_analytics` schema under the `workspace` catalog. Leave managed storage at its default.
2. Select `workspace.rugby_analytics`, then choose **Create > Volume**. Name it `landing`, choose **Managed**, and leave its storage location at the default.
3. Upload `data/landing/urc-2024-25-47ce925d0db9.jsonl` to the volume. The destination path should be `/Volumes/workspace/rugby_analytics/landing/urc-2024-25-47ce925d0db9.jsonl`. See the [Databricks volume upload instructions](https://docs.databricks.com/aws/en/volumes/volume-files).
4. Import [`ingest_notebook.py`](ingest_notebook.py) into your Databricks workspace as a notebook. The first-line marker tells Databricks to recognize it as a Python notebook; see [notebook import instructions](https://docs.databricks.com/aws/en/notebooks/notebook-export-import).
5. Run the notebook on Free Edition serverless compute. Its default widgets target the path above. The first run reported 151 source matches, 151 new match versions, 151 current matches, and zero score discrepancies. A repeat run reported zero new match versions, 151 current matches, and zero score discrepancies (user-reported output, 28 September 2026).
6. Import [`gold_notebook.py`](gold_notebook.py) as a second notebook and run it on serverless compute. It builds `dim_team`, `fact_match`, `gold_team_season`, and `gold_player_scoring` as managed Delta tables. The verified run reported 151 current matches, 151 match facts, 16 teams, 302 team appearances, and 7,313 points on both sides of the reconciliation (user-reported output, 28 September 2026). The top five teams by wins are Leinster Rugby, Vodacom Bulls, Hollywoodbets Sharks, Glasgow Warriors, and DHL Stormers.

The ingestion notebook writes managed Delta tables in `workspace.rugby_analytics`. The Azure-specific job under `cloud/databricks/` cannot read this AWS-hosted Free Edition workspace's volume without adaptation. The dbt models under `cloud/dbt/` have now been built against this workspace with 22 passing tests.

The [dbt project](../dbt/README.md) builds into a separate schema so its results can be compared with the notebook Gold tables.

Free Edition has serverless usage quotas; the workspace can pause compute when a quota is reached. The [Free Edition limits](https://docs.databricks.com/aws/en/getting-started/free-edition-limitations) describe those limits.
