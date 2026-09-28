SELECT d.team_name, p.player, p.tries, p.recorded_points
FROM workspace.rugby_dbt.player_scoring p
JOIN workspace.rugby_dbt.dim_team d ON p.team_id = d.team_id
WHERE p.season = '2024-25'
ORDER BY p.tries DESC, p.recorded_points DESC, p.player
LIMIT 20
