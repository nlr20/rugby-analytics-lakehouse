# Five-season rugby dashboard datasets

These read-only queries use the `workspace.rugby_dbt` marts. The [five-season dbt build](../dbt/README.md) has passed; the existing 2024–25 three-view dashboard was built manually. These multi-season queries and the two new views have **not** been run in that dashboard yet.

| Query | Suggested view | Meaning |
| --- | --- | --- |
| [Team performance](01_team_performance.sql) | Bar chart filtered by season | Wins, win percentage and scoring difference, including playoffs |
| [Team results by venue](02_home_advantage.sql) | Pie chart by result, filtered by season and team | Home/away wins, draws and losses from each team's perspective; use `Count(outcome)` because each row is one team in one match |
| [Player scoring](03_player_scoring.sql) | Table filtered by season and team | Top 20 listed try scorers per team and their recorded points |
| [Fixture schedule](04_fixture_schedule.sql) | Table filtered by season/team/status | Results and fixtures whose result is unavailable in the source |
| [Team trend](05_team_trend.sql) | Line chart | Team wins and point difference across seasons |

In Databricks: **New > Dashboard > Data > Add SQL dataset**, paste a query and run it; add a widget on the Canvas. Add a `season` filter so viewers can compare like with like. The team-performance view is not an official league table: it includes playoff matches and does not calculate bonus points. Player scoring is based on listed events, which have one documented gap in 2022–23. Results marked `result_unavailable` may have dates in the past; the source snapshot has no final score for them.

## How the five datasets relate

| Dataset | Grain | Team link |
| --- | --- | --- |
| Team performance | One row per team per season | `season_team_key`; hub for a season/team |
| Team results by venue (previously Home advantage) | One row per team per completed match | Many-to-one to Team performance on `season_team_key` |
| Player scoring | Several player rows per team per season | Many-to-one to Team performance on `season_team_key` |
| Team trend | One row per team per season | Same `season_team_key` as Team performance |
| Fixture Schedule | One row per fixture | `match_id`; team appears in either `home_team` or `away_team` |

Fixture Schedule cannot use a single `season_team_key` without duplicating each fixture or losing the seven `TBC` fixtures. Its SQL accepts a `:team` parameter and filters on `home_team = :team OR away_team = :team`; `All` or null preserves the full schedule. In the dataset editor, set the parameter's default to `All` so the query can run before the dashboard filter is configured.

In the dashboard Relationships editor, connect Team performance's `season_team_key` (one side) to the same field in Team results by venue, Player scoring, and Team Trend (many side). Team Trend currently has one row per team-season, but the editor offers only One-to-Many or Many-to-One. These relationships allow a selection in the team performance chart to filter the connected charts. Fixture Schedule still needs a separate team parameter because one fixture has both a home and an away team. A global Single value **Team** control can combine the team fields of the four related datasets with Fixture Schedule's `team` parameter; see [query-based field and parameter controls](https://docs.databricks.com/aws/en/dashboards/manage/filters/parameters).

The venue dataset has two team appearances per completed match. Its pie chart should use `outcome` as the category and `Count(outcome)` as the value; an unfiltered chart therefore totals two appearances per match. Give it the title **Team results by venue** rather than treating it as the old whole-league home advantage count.

See [Databricks dashboard datasets](https://docs.databricks.com/aws/en/dashboards/manage/data-modeling/datasets) and [visualization setup](https://docs.databricks.com/aws/en/dashboards/manage/visualizations).
