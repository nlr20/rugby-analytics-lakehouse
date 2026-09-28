select
    match_id, season, played_at,
    sha2(home_team, 256) as home_team_id,
    sha2(away_team, 256) as away_team_id,
    home_score, away_score, attendance,
    case when home_score > away_score then sha2(home_team, 256)
         when away_score > home_score then sha2(away_team, 256)
    end as winner_team_id
from {{ ref('stg_latest_matches') }}

