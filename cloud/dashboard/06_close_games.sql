SELECT t.season, d.team_name,
       concat(t.season, '|', t.team_id) AS season_team_key,
       count(*) AS played,
       sum(CASE WHEN abs(t.points_for - t.points_against) <= 5 AND t.result = 'Win' THEN 1 ELSE 0 END) AS close_wins,
       sum(CASE WHEN abs(t.points_for - t.points_against) <= 5 AND t.result = 'Loss' THEN 1 ELSE 0 END) AS close_losses,
       sum(CASE WHEN t.result = 'Draw' THEN 1 ELSE 0 END) AS draws,
       sum(CASE WHEN abs(t.points_for - t.points_against) <= 5 THEN 1 ELSE 0 END) AS close_matches
FROM workspace.rugby_dbt.team_match t
JOIN workspace.rugby_dbt.dim_team d ON t.team_id = d.team_id
GROUP BY t.season, d.team_name, t.team_id
ORDER BY t.season DESC, close_wins DESC, d.team_name
