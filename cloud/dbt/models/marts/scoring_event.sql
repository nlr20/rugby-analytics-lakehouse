select e.event_id, e.match_id, m.season,
       sha2(e.team, 256) as team_id,
       e.side, e.minute, e.event_type, e.player, e.points
from {{ source('silver', 'silver_scoring_versions') }} e
join {{ ref('stg_latest_matches') }} m
  on e.match_id = m.match_id
 and e.source_hash = m.source_hash
 and e.transform_version = m.transform_version
