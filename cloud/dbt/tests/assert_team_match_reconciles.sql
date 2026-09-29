with facts as (
    select count(*) as matches,
           sum(case when home_score = away_score then 1 else 0 end) as drawn_matches,
           sum(home_score + away_score) as match_points
    from {{ ref('fact_match') }}
), team_results as (
    select count(*) as appearances,
           sum(case when result = 'Win' then 1 else 0 end) as wins,
           sum(case when result = 'Draw' then 1 else 0 end) as draws,
           sum(points_for) as team_points
    from {{ ref('team_match') }}
)
select * from facts cross join team_results
where appearances != 2 * matches
   or wins != matches - drawn_matches
   or draws != 2 * drawn_matches
   or team_points != match_points
