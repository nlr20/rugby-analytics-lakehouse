with sides as (
    select season, home_team_id as team_id, home_score as points_for,
           away_score as points_against,
           cast(home_score > away_score as int) as win,
           cast(home_score = away_score as int) as draw
    from {{ ref('fact_match') }}
    union all
    select season, away_team_id, away_score, home_score,
           cast(away_score > home_score as int),
           cast(home_score = away_score as int)
    from {{ ref('fact_match') }}
)
select season, team_id, count(*) as played, sum(win) as wins,
       sum(draw) as draws, sum(points_for) as points_for,
       sum(points_against) as points_against
from sides
group by season, team_id

