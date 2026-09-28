{{ config(materialized='view') }}

select m.*
from {{ source('silver', 'silver_match_versions') }} m
join {{ ref('stg_current_fixtures') }} f
  on m.match_id = f.match_id
 and m.source_hash = f.source_hash
 and m.transform_version = f.transform_version
where f.status = 'completed'

