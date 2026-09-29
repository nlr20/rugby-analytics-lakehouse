# Power BI Desktop reporting plan

Power BI is the final reporting layer for the five-season model. Databricks Silver ingestion and dbt Gold were validated on 29 September 2026. No `.pbix` file or published report is claimed yet.

In Power BI Desktop, choose **Get data > Databricks**. For this AWS-hosted SQL warehouse with OAuth, use the **Databricks** connector, enter the server hostname and HTTP path from **SQL Warehouses > Connection Details**, and sign in. Choose **Import** for a small portfolio dataset so the report can be viewed without a live query on every interaction. Microsoft's [Databricks Power Query connector guide](https://learn.microsoft.com/en-us/power-query/connectors/databricks) covers the AWS OAuth path.

Load these dbt tables from `workspace.rugby_dbt`:

| Table | Use |
| --- | --- |
| `dim_team` | Team labels and team ID |
| `fact_match` | Completed scores, dates, season and winner |
| `team_season` | Wins, draws, points for/against by season and team |
| `team_match` | One row per team's match appearance, including home/away venue and result |
| `player_scoring` | Named try scorers and listed scoring points |
| `fixture_schedule` | All fixtures, including missing source results |

Join `team_season.team_id` and `player_scoring.team_id` to `dim_team.team_id`. Keep `fact_match` home and away team IDs as separate role-playing relationships or use the already modelled team-season table for simple team visuals. Suggested pages: **Season overview** (season selector, completed versus result-unavailable fixtures, wins by team), **Team trends** (wins and point difference across seasons), **Matches** (fixture/result table), and **Players** (top try scorers). Label win rates as all matches including playoffs, and player points as recorded scoring events. Do not show the 67 unscored 2025–26 fixtures as future matches.

Verify the imported totals against [the audit](../../docs/multiseason-audit.md) before saving the report: 755 fixtures, 688 completed matches and 67 without results for the audited source files. Power BI Desktop is the intended no-cost authoring path; publishing a service report may have separate licensing requirements.
