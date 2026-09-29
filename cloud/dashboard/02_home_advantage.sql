SELECT t.season, d.team_name,
       concat(t.season, '|', t.team_id) AS season_team_key,
       concat(t.venue, ' ', lower(t.result)) AS outcome,
       count(*) AS matches
FROM workspace.rugby_dbt.team_match t
JOIN workspace.rugby_dbt.dim_team d ON t.team_id = d.team_id
GROUP BY t.season, d.team_name, t.team_id, t.venue, t.result
ORDER BY t.season DESC, d.team_name, outcome
