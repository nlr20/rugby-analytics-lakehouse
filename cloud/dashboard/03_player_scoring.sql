WITH ranked AS (
  SELECT p.season, d.team_name,
         concat(p.season, '|', p.team_id) AS season_team_key,
         p.player, p.tries, p.recorded_points,
         row_number() OVER (PARTITION BY p.season, p.team_id
                            ORDER BY p.tries DESC, p.recorded_points DESC, p.player) AS season_rank
  FROM workspace.rugby_dbt.player_scoring p
  JOIN workspace.rugby_dbt.dim_team d ON p.team_id = d.team_id
)
SELECT season, team_name, season_team_key, player, tries, recorded_points, season_rank
FROM ranked
WHERE season_rank <= 20
ORDER BY season DESC, season_rank
