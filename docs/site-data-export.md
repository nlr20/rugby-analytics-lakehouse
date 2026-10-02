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
| `stadiums.json` | One row per named stadium | All-season recorded-match count, attendance coverage, listed-home wins, draws, close games (margin ≤7) and average combined points. Names are source labels, not yet verified physical venues. |
| `ground_matches.json` | One row per completed match with a named ground | The fixture-to-ground link, season, date, teams, scores and numeric attendance for ground profiles, fixture filters and attendance trends. `match_id` joins `fixtures.json`. |

`ground_matches` is an additive version-1 dataset: the existing website preview can keep loading its original eight datasets until its Grounds tab is updated. The new export reconciles each ground match with its fixture and every `stadiums.json` count with the underlying matches. `matches_with_named_ground` and `matches_without_named_ground` in manifest quality show ground coverage.

The feed identifies a **listed home side**, but does not state whether the match took place at that team's usual ground or at a neutral venue. `neutral_venue` is therefore `null` and `listed_home_wins` must not be presented as a neutral-adjusted home advantage or home win rate. The site can calculate the listed home side's win percentage if it uses that exact label and shows the match count. `close_matches` counts score margins of seven or fewer points, including draws. `average_combined_points` is points by both sides per match. Attendance values are in `ground_matches.json`; the stadium coverage field counts matches with a value, not spectators.

The export does not yet contain city, country or coordinates. A separate, source-verified venue lookup is still needed before plotting markers. Some source labels may be naming-rights aliases for the same physical ground; keep the source label as the join key and reconcile aliases only with evidence.

For the Grounds tab, join `stadiums.stadium_name` to `ground_matches.stadium_name`. Use `completed_matches` for the ranked bars. Filter `ground_matches` by `season` and by either `home_team` or `away_team` for the selected ground's fixtures. A listed-home win percentage is `listed_home_wins / completed_matches`, and close-game frequency is `close_matches / completed_matches`; show the denominator alongside both. Actual attendance trends should aggregate the non-null numeric `attendance` values by season and show the number of reporting matches. No attendance estimate should be inferred for the one missing value in the current snapshot.

The manifest's `quality` section records reconciliation totals and the difference between listed event points and final-score points. After the [2025–26 backfill](direct-api-backfill.md) and [2022–23 single-match repair](2022-23-match-repair.md), the current export has 755 completed matches, zero unavailable results and **zero score-event point gap**: listed events and final scores each total 36,826 points. Team wins include playoffs and are not official league-table standings.

The exporter checks unique fixture, team and ground-match keys; one home and one away appearance per completed match; fixture scores versus team scores; team-season and stadium totals; and snapshot stability during extraction. It aborts before publishing a new manifest if a check fails.

## Public release boundary

The [community rugby source](https://github.com/transientlunatic/Rugby-Data) has no clear reuse licence in the [source audit](source-audit.md), and the direct match feed's public redistribution rights have not been confirmed. Confirm permission or switch to a licensed source before placing derived rugby records on a public site. The generated bundle stays under ignored `data/` until that decision. The map also needs a checked stadium-to-coordinate lookup and OpenStreetMap attribution before publication.
