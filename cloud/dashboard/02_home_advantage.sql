SELECT season, CASE WHEN home_score > away_score THEN 'Home win'
            WHEN away_score > home_score THEN 'Away win'
            ELSE 'Draw' END AS outcome,
       count(*) AS matches
FROM workspace.rugby_dbt.fact_match
GROUP BY season, outcome
ORDER BY season DESC, matches DESC
