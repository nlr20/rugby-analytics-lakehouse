with current_events as (
    select e.match_id, m.season, e.team, e.player, e.event_type, e.points
    from {{ source('silver', 'silver_scoring_versions') }} e
    join {{ ref('stg_latest_matches') }} m
      on e.match_id = m.match_id and e.source_hash = m.source_hash
     and e.transform_version = m.transform_version
    where e.player is not null
)
select season, sha2(team, 256) as team_id, player,
       sum(case when event_type = 'Try' then 1 else 0 end) as tries,
       sum(points) as recorded_points
from current_events
group by season, team, player

