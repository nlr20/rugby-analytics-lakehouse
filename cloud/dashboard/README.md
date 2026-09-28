# Rugby season dashboard

Three read-only datasets for a Databricks AI/BI dashboard, built from the verified `workspace.rugby_dbt` models:

1. [Team performance](01_team_performance.sql): wins, win percentage, and scoring difference. Include knockout matches, so this is **not** an official URC league table and omits bonus points.
2. [Home advantage](02_home_advantage.sql): count of home wins, away wins, and draws.
3. [Player scoring](03_player_scoring.sql): top 20 named players by tries, with points from listed scoring events. The source does not contain complete all-round player performance data.

To build the dashboard manually in Databricks, choose **New > Dashboard**, open its **Data** tab, choose **Add SQL dataset**, paste one query, and run it. Rename each dataset to match its file. On the **Canvas** tab, use a table for team performance, a bar chart for outcomes, and a bar chart or table for player tries. Add a text note explaining the scope above. This dashboard has not yet been created in the workspace.

See [Databricks dashboard datasets](https://docs.databricks.com/aws/en/dashboards/manage/data-modeling/datasets) and [visualization setup](https://docs.databricks.com/aws/en/dashboards/manage/visualizations). Published Databricks dashboards are shared with registered users of the same Databricks account; a portfolio screenshot can show the result to recruiters without requiring them to sign in.
