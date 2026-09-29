SELECT match_id, season, status, played_at, round_type, round_number,
       home_team, away_team, home_score, away_score
FROM workspace.rugby_dbt.fixture_schedule
WHERE :team IS NULL OR :team = 'All'
   OR home_team = :team OR away_team = :team
ORDER BY season DESC, played_at, round_number
