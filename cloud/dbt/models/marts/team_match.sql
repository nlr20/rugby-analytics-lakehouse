select match_id, season, played_at, home_team_id as team_id,
       concat(match_id, '|', home_team_id) as match_team_key,
       'Home' as venue,
       case when home_score > away_score then 'Win'
            when home_score = away_score then 'Draw'
            else 'Loss' end as result,
       home_score as points_for, away_score as points_against
from {{ ref('fact_match') }}
union all
select match_id, season, played_at, away_team_id as team_id,
       concat(match_id, '|', away_team_id) as match_team_key,
       'Away' as venue,
       case when away_score > home_score then 'Win'
            when away_score = home_score then 'Draw'
            else 'Loss' end as result,
       away_score as points_for, home_score as points_against
from {{ ref('fact_match') }}
