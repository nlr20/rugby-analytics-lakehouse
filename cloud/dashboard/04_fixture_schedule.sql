SELECT season, status, played_at, round_type, round_number,
       home_team, away_team, home_score, away_score
FROM workspace.rugby_dbt.fixture_schedule
ORDER BY season DESC, played_at, round_number
