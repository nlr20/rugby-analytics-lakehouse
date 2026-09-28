with match_totals as (
    select count(*) as matches,
           sum(home_score + away_score) as points
    from {{ ref('fact_match') }}
),
team_totals as (
    select sum(played) as appearances,
           sum(points_for) as points
    from {{ ref('team_season') }}
)
select m.matches, m.points as match_points,
       t.appearances, t.points as team_points
from match_totals m cross join team_totals t
where t.appearances != 2 * m.matches
   or t.points != m.points
