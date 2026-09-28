select match_id, season, status, round_type, round_number, played_at,
       home_team, away_team, home_score, away_score
from {{ ref('stg_current_fixtures') }}
