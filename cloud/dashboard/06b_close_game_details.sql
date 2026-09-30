SELECT t.match_id, t.season, d.team_name,
       concat(t.season, '|', t.team_id) AS season_team_key,
       t.played_at, o.team_name AS opponent,
       t.venue, t.result,
       t.points_for, t.points_against,
       t.points_for - t.points_against AS point_difference
FROM workspace.rugby_dbt.team_match t
JOIN workspace.rugby_dbt.fact_match f ON t.match_id = f.match_id
JOIN workspace.rugby_dbt.dim_team d ON t.team_id = d.team_id
JOIN workspace.rugby_dbt.dim_team o
  ON o.team_id = CASE WHEN t.venue = 'Home' THEN f.away_team_id ELSE f.home_team_id END
WHERE abs(t.points_for - t.points_against) <= 5
ORDER BY t.season DESC, t.played_at DESC, d.team_name
