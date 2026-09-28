SELECT CASE WHEN home_score > away_score THEN 'Home win'
            WHEN away_score > home_score THEN 'Away win'
            ELSE 'Draw' END AS outcome,
       count(*) AS matches
FROM workspace.rugby_dbt.fact_match
WHERE season = '2024-25'
GROUP BY 1
ORDER BY matches DESC
