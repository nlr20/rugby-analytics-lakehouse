# Five-season rugby dashboard datasets

These read-only queries use the `workspace.rugby_dbt` marts. The first five datasets cover team performance, results by venue, player scoring, fixtures and team trends. The three additional datasets below extend the dashboard with close games, scoring patterns and head-to-head records.

| Query | Suggested view | Meaning |
| --- | --- | --- |
| [Team performance](01_team_performance.sql) | Bar chart filtered by season | Wins, win percentage and scoring difference, including playoffs |
| [Team results by venue](02_home_advantage.sql) | Pie chart by result, filtered by season and team | Home/away wins, draws and losses from each team's perspective; use `Count(outcome)` because each row is one team in one match |
| [Player scoring](03_player_scoring.sql) | Table filtered by season and team | Top 20 listed try scorers per team and their recorded points |
| [Fixture schedule](04_fixture_schedule.sql) | Table filtered by season/team/status | Results and fixtures whose result is unavailable in the source |
| [Team trend](05_team_trend.sql) | Line chart | Team wins and point difference across seasons |
| [Close games](06_close_games.sql) | Bars of `close_wins` and `close_losses` by `team_name` | Matches decided by five points or fewer, including playoffs; `avg_close_margin` summarises their absolute point difference |
| [Close game details](06b_close_game_details.sql) | Table of date, `opponent`, result, scores and `point_difference` | One row per team's close match; signed point difference is positive for a win, negative for a loss, and zero for a draw |
| [Scoring patterns](07_scoring_patterns.sql) | Bars of **Sum of `points`** by `match_period` or `event_type` | When points were scored and how; missed attempts contribute zero points |
| [Head-to-head](08_head_to_head.sql) | Table of `opponent`, `played`, `wins`, `draws`, `losses` | A selected team's record against each opponent |

In Databricks: **New > Dashboard > Data > Add SQL dataset**, paste a query and run it; add a widget on the Canvas. Add a `season` filter so viewers can compare like with like. The team-performance view is not an official league table: it includes playoff matches and does not calculate bonus points. Player scoring is based on listed events; the previously missing 2022–23 match detail has been repaired in the current snapshot. The current five-season snapshot has no fixtures with `result_unavailable` status.

## How the datasets relate

| Dataset | Grain | Team link |
| --- | --- | --- |
| Team performance | One row per team per season | `season_team_key`; hub for a season/team |
| Team results by venue (previously Home advantage) | One row per team per completed match | Many-to-one to Team performance on `season_team_key` |
| Player scoring | Several player rows per team per season | Many-to-one to Team performance on `season_team_key` |
| Team trend | One row per team per season | Same `season_team_key` as Team performance |
| Fixture Schedule | One row per fixture | `match_id`; team appears in either `home_team` or `away_team` |
| Close games | One row per team per season | Same `season_team_key` as Team performance |
| Close game details | One row per team per close match | Many-to-one to Team performance on `season_team_key` |
| Scoring patterns | One row per listed event | Many-to-one to Team performance on `season_team_key` |
| Head-to-head | One row per team, season and opponent | Many-to-one to Team performance on `season_team_key` |

Fixture Schedule cannot use a single `season_team_key` without duplicating each fixture, because one fixture has both a home and an away team. Its SQL accepts a `:team` parameter and filters on `home_team = :team OR away_team = :team`; `All` or null preserves the full schedule. In the dataset editor, set the parameter's default to `All` so the query can run before the dashboard filter is configured.

In the dashboard Relationships editor, connect Team performance's `season_team_key` (one side) to the same field in Team results by venue, Player scoring, Team Trend, Close games, Close game details, Scoring patterns and Head-to-head (many side). Team Trend and Close games currently have one row per team-season, but the editor offers only One-to-Many or Many-to-One. These relationships allow a selection in the team performance chart to filter the connected charts. Fixture Schedule still needs a separate team parameter because one fixture has both a home and an away team. A global Single value **Team** control can combine the team fields of the related datasets with Fixture Schedule's `team` parameter; see [query-based field and parameter controls](https://docs.databricks.com/aws/en/dashboards/manage/filters/parameters).

The venue dataset has two team appearances per completed match. Its pie chart should use `outcome` as the category and `Count(outcome)` as the value; an unfiltered chart therefore totals two appearances per match. Give it the title **Team results by venue** rather than treating it as the old whole-league home advantage count.

The `scoring_event` dbt mart follows the latest completed version of each match, so corrected snapshots do not double count old events. The repaired 2022–23 Glasgow Warriors versus Vodacom Bulls match now includes its scoring events and player lineups. All five current season snapshots have 151 completed matches, and listed event points reconcile with final-score points. The team comparisons include knockout games and are not official league standings.

See [Databricks dashboard datasets](https://docs.databricks.com/aws/en/dashboards/manage/data-modeling/datasets) and [visualization setup](https://docs.databricks.com/aws/en/dashboards/manage/visualizations).
