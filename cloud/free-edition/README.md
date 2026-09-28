# Databricks Free Edition setup

This is the no-cost development path for the available AWS-hosted Databricks Free Edition workspace. It uses Databricks-managed storage; it does not deploy Azure resources. The workspace steps are pending manual verification, so this is not yet an end-to-end deployment claim.

## Prepare the landing file locally

From the repository root, install the package and run:

```bash
python -m pip install -e '.[dev]'
rugby-lakehouse prepare-landing --source-ref c2de981ddcbcf2362fdc5719eefa6d9172740850
```

This validates the 151-match snapshot, derives match and event fields, and writes a file named `data/landing/urc-2024-25-<snapshot-hash>.jsonl`. For the audited revision, the exact filename is `urc-2024-25-47ce925d0db9.jsonl`. The season distinguishes future seasons; the hash preserves separate snapshots when the same season is corrected. Each line contains both the unchanged upstream `raw` record and a normalized `match` record. The file and all generated data are ignored by Git. To use an already-downloaded snapshot without network access, add `--input path/to/source-snapshot.json`.

The current transform handles **2024–25 only**. Adding another season also requires parameterizing the season in the fixture identity and validating the new source file; the filename convention alone does not add multi-season processing.

## Workspace steps pending verification

1. In Catalog Explorer, create the `rugby_analytics` schema under the `workspace` catalog. Leave managed storage at its default.
2. Select `workspace.rugby_analytics`, then choose **Create > Volume**. Name it `landing`, choose **Managed**, and leave its storage location at the default.
3. Upload `data/landing/urc-2024-25-47ce925d0db9.jsonl` to the volume. The destination path should be `/Volumes/workspace/rugby_analytics/landing/urc-2024-25-47ce925d0db9.jsonl`. See the [Databricks volume upload instructions](https://docs.databricks.com/aws/en/volumes/volume-files).
4. Import [`ingest_notebook.py`](ingest_notebook.py) into your Databricks workspace as a notebook. The first-line marker tells Databricks to recognize it as a Python notebook; see [notebook import instructions](https://docs.databricks.com/aws/en/notebooks/notebook-export-import).
5. Run the notebook on Free Edition serverless compute. Its default widgets target the path above. On the first run it should report 151 source matches, 151 new match versions, 151 current matches, and zero score discrepancies. A repeated run of the same file should report zero new match versions.

The notebook writes managed Delta tables in `workspace.rugby_analytics`. It has not yet run in this workspace, so the expected results above are verification targets rather than a claim of completed deployment. The Azure-specific job under `cloud/databricks/` cannot read this AWS-hosted Free Edition workspace's volume without adaptation.

Free Edition has serverless usage quotas; the workspace can pause compute when a quota is reached. The [Free Edition limits](https://docs.databricks.com/aws/en/getting-started/free-edition-limitations) describe those limits.
