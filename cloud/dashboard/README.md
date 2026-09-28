# Five-season rugby dashboard datasets

These read-only queries use the `workspace.rugby_dbt` marts. Run the [five-season dbt build](../dbt/README.md) before replacing dashboard datasets. The existing 2024–25 three-view dashboard was built manually; these multi-season queries and the two new views have **not** been run in that dashboard yet.

| Query | Suggested view | Meaning |
| --- | --- | --- |
| [Team performance](01_team_performance.sql) | Bar chart filtered by season | Wins, win percentage and scoring difference, including playoffs |
| [Home advantage](02_home_advantage.sql) | Stacked bars by season | Home wins, away wins, draws |
| [Player scoring](03_player_scoring.sql) | Table filtered by season | Top listed try scorers and recorded points |
| [Fixture schedule](04_fixture_schedule.sql) | Table filtered by season/status | Results and fixtures whose result is unavailable in the source |
| [Team trend](05_team_trend.sql) | Line chart | Team wins and point difference across seasons |

In Databricks: **New > Dashboard > Data > Add SQL dataset**, paste a query and run it; add a widget on the Canvas. Add a `season` filter so viewers can compare like with like. The team-performance view is not an official league table: it includes playoff matches and does not calculate bonus points. Player scoring is based on listed events, which have one documented gap in 2022–23. Results marked `result_unavailable` may have dates in the past; the source snapshot has no final score for them.

See [Databricks dashboard datasets](https://docs.databricks.com/aws/en/dashboards/manage/data-modeling/datasets) and [visualization setup](https://docs.databricks.com/aws/en/dashboards/manage/visualizations).
