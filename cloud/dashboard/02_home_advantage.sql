SELECT t.match_id, t.season, d.team_name,
       concat(t.season, '|', t.team_id) AS season_team_key,
       concat(t.venue, ' ', lower(t.result)) AS outcome
FROM workspace.rugby_dbt.team_match t
JOIN workspace.rugby_dbt.dim_team d ON t.team_id = d.team_id
ORDER BY t.season DESC, d.team_name, t.match_id
