# Rugby website data export

The career website can render interactive charts from a **static, versioned copy** of the current Databricks Gold data. Browser visitors do not connect to the SQL warehouse. The existing Databricks dashboard remains an authoring and engineering view; this export is the app boundary.

## Run locally

After ingestion and `dbt build` have succeeded, install the optional connector dependency and export with your own browser OAuth login:

```powershell
pip install -e '.[site-export]'
$env:DATABRICKS_HOST='dbc-ac97a731-fd87.cloud.databricks.com'
$env:DATABRICKS_HTTP_PATH='/sql/1.0/warehouses/225860b399aaa73c'
python -m rugby_lakehouse.site_export --output data/site-export
```

The `data/` directory is Git-ignored. This command creates **local preview files only**. It does not deploy a website or commit rugby data. No Databricks secret is placed in the files. For a future unattended refresh, use a server-side service principal if the account supports it, with credentials in the automation's secret store. Never put warehouse credentials in React code.

## Contract, version 1

The website loads `manifest.json` first. Its `datasets` entries contain a relative `path`, `rows` count and SHA-256 digest. Each path points into an immutable `snapshots/<export-id>/` directory; the exporter writes the manifest **last**, so a site build reading it does not pick up half-written files. The app can fetch each JSON array by its manifest path and use `season_team_key` (`season|team_id`) to coordinate team and season selections.

| File | Grain | Website use |
| --- | --- | --- |
| `seasons.json` | One current snapshot per season | Available seasons, source snapshot hash, source ingestion time and status counts |
| `teams.json` | One row per team | Team selector and canonical names |
| `team_seasons.json` | One row per team-season | Performance and trend charts |
| `fixtures.json` | One row per current fixture | Match list, scores and `result_unavailable` status |
| `team_matches.json` | Two rows per completed match | Team results, close games, opponents and head-to-head filters |
| `player_scoring.json` | One row per player-team-season | Listed tries and recorded points |
| `scoring_patterns.json` | One row per team-season-period-event type | Event counts and points by type and match period |
| `stadiums.json` | One row per named stadium | Stadium inventory awaiting verified coordinates; **not yet map points** |

The manifest's `quality` section records reconciliation totals and the difference between listed event points and final-score points. This gap is currently 56 points: a 2022–23 Glasgow Warriors 35–21 Vodacom Bulls match lacks listed scoring events. The [direct feed backfill](direct-api-backfill.md) has supplied all 151 results for 2025–26, so the current export has 755 completed matches and zero unavailable results. Team wins include playoffs and are not official league-table standings.

The exporter checks unique fixture and team keys, one home and one away appearance per completed match, fixture scores versus team scores, team-season appearance counts, and snapshot stability during extraction. It aborts before publishing a new manifest if a check fails.

## Public release boundary

The [community rugby source](https://github.com/transientlunatic/Rugby-Data) has no clear reuse licence in the [source audit](source-audit.md), and the direct match feed's public redistribution rights have not been confirmed. Confirm permission or switch to a licensed source before placing derived rugby records on a public site. The generated bundle stays under ignored `data/` until that decision. The map also needs a checked stadium-to-coordinate lookup and OpenStreetMap attribution before publication.
