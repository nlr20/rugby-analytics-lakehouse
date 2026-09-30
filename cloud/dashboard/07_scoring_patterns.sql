SELECT e.season, d.team_name,
       concat(e.season, '|', e.team_id) AS season_team_key,
       e.event_id, e.match_id, e.event_type, e.minute, e.points,
       CASE WHEN e.minute <= 20 THEN '0–20'
            WHEN e.minute <= 40 THEN '21–40'
            WHEN e.minute <= 60 THEN '41–60'
            WHEN e.minute <= 80 THEN '61–80'
            ELSE '81+' END AS match_period,
       CASE WHEN e.minute <= 20 THEN 1
            WHEN e.minute <= 40 THEN 2
            WHEN e.minute <= 60 THEN 3
            WHEN e.minute <= 80 THEN 4
            ELSE 5 END AS period_order
FROM workspace.rugby_dbt.scoring_event e
JOIN workspace.rugby_dbt.dim_team d ON e.team_id = d.team_id
ORDER BY e.season DESC, d.team_name, e.match_id, e.minute
