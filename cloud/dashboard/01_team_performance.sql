SELECT d.team_name, g.played, g.wins, g.draws,
       g.played - g.wins - g.draws AS losses,
       round(100.0 * g.wins / g.played, 1) AS win_percentage,
       g.points_for, g.points_against,
       g.points_for - g.points_against AS points_difference
FROM workspace.rugby_dbt.team_season g
JOIN workspace.rugby_dbt.dim_team d ON g.team_id = d.team_id
WHERE g.season = '2024-25'
ORDER BY g.wins DESC, points_difference DESC, d.team_name
