# Rugby season dashboard

Three read-only datasets for a Databricks AI/BI dashboard, built from the verified `workspace.rugby_dbt` models:

1. [Team performance](01_team_performance.sql): wins, win percentage, and scoring difference. Include knockout matches, so this is **not** an official URC league table and omits bonus points.
2. [Home advantage](02_home_advantage.sql): count of home wins, away wins, and draws.
3. [Player scoring](03_player_scoring.sql): top 20 named players ranked by tries, with points from listed scoring events as extra context. Title this view **Most tries by player**. The source does not contain complete all-round player performance data.

To build the dashboard manually in Databricks, choose **New > Dashboard**, open its **Data** tab, choose **Add SQL dataset**, paste one query, and run it. Rename each dataset to match its file. On the **Canvas** tab, use a bar chart for team wins, a bar chart for outcomes, and a table for player tries. Add a text note explaining the scope above. The three datasets and widgets were created manually in the workspace; the full layout and publication have not yet been reviewed.

The manually run outcome query returned 98 home wins, 49 away wins, and 4 draws, reconciling to 151 fixtures. The player query returned 20 rows, headed by six players with 9 tries each (user-reported results, 28 September 2026).

See [Databricks dashboard datasets](https://docs.databricks.com/aws/en/dashboards/manage/data-modeling/datasets) and [visualization setup](https://docs.databricks.com/aws/en/dashboards/manage/visualizations). Published Databricks dashboards are shared with registered users of the same Databricks account; a portfolio screenshot can show the result to recruiters without requiring them to sign in.
