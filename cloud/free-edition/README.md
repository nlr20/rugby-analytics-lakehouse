# Databricks Free Edition setup

This is the no-cost development path for the available AWS-hosted Databricks Free Edition workspace. It uses Databricks-managed storage; it does not deploy Azure resources. The workspace steps are pending manual verification, so this is not yet an end-to-end deployment claim.

## Prepare the landing file locally

From the repository root, install the package and run:

```bash
python -m pip install -e '.[dev]'
rugby-lakehouse prepare-landing --source-ref c2de981ddcbcf2362fdc5719eefa6d9172740850
```

This validates the 151-match snapshot, derives match and event fields, and writes `data/landing/matches.jsonl`. Each line contains both the unchanged upstream `raw` record and a normalized `match` record. The file and all generated data are ignored by Git. To use an already-downloaded snapshot without network access, add `--input path/to/source-snapshot.json`.

## Workspace step pending verification

Create a managed volume in a catalog and schema where you have write access, then upload `data/landing/matches.jsonl` through Databricks Catalog Explorer. The [Databricks volume upload instructions](https://docs.databricks.com/aws/en/ingestion/file-upload/) describe the UI. The next step is to run and verify the Delta ingestion job against the uploaded volume path; the Azure-specific job under `cloud/databricks/` cannot read this AWS-hosted Free Edition workspace's volume without adaptation.

Free Edition has serverless usage quotas; the workspace can pause compute when a quota is reached. The [Free Edition limits](https://docs.databricks.com/aws/en/getting-started/free-edition-limitations) describe those limits.
