SELECT g.season, d.team_name, concat(g.season, '|', g.team_id) AS season_team_key,
       g.played, g.wins, g.draws,
       g.played - g.wins - g.draws AS losses,
       round(100.0 * g.wins / g.played, 1) AS win_percentage,
       g.points_for, g.points_against,
       g.points_for - g.points_against AS points_difference
FROM workspace.rugby_dbt.team_season g
JOIN workspace.rugby_dbt.dim_team d ON g.team_id = d.team_id
ORDER BY g.season DESC, g.wins DESC, points_difference DESC, d.team_name
