WITH appearances AS (
  SELECT t.season, t.team_id, t.result, t.points_for, t.points_against,
         CASE WHEN t.venue = 'Home' THEN f.away_team_id ELSE f.home_team_id END AS opponent_team_id
  FROM workspace.rugby_dbt.team_match t
  JOIN workspace.rugby_dbt.fact_match f ON t.match_id = f.match_id
)
SELECT a.season, d.team_name,
       concat(a.season, '|', a.team_id) AS season_team_key,
       o.team_name AS opponent,
       count(*) AS played,
       sum(CASE WHEN a.result = 'Win' THEN 1 ELSE 0 END) AS wins,
       sum(CASE WHEN a.result = 'Draw' THEN 1 ELSE 0 END) AS draws,
       sum(CASE WHEN a.result = 'Loss' THEN 1 ELSE 0 END) AS losses,
       sum(a.points_for) AS points_for,
       sum(a.points_against) AS points_against
FROM appearances a
JOIN workspace.rugby_dbt.dim_team d ON a.team_id = d.team_id
JOIN workspace.rugby_dbt.dim_team o ON a.opponent_team_id = o.team_id
GROUP BY a.season, d.team_name, a.team_id, o.team_name
ORDER BY a.season DESC, d.team_name, wins DESC, o.team_name
