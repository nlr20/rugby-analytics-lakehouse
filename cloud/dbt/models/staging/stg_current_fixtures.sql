{{ config(materialized='view') }}

with latest_snapshots as (
    select season, source_snapshot_hash, transform_version
    from (
        select season, source_snapshot_hash, transform_version,
               row_number() over (
                   partition by season order by ingested_at desc, transform_version desc, source_snapshot_hash desc
               ) as version_rank
        from {{ source('silver', 'silver_season_snapshots') }}
    ) where version_rank = 1
)
select f.*
from {{ source('silver', 'silver_fixture_versions') }} f
join latest_snapshots s
  on f.season = s.season and f.source_snapshot_hash = s.source_snapshot_hash
 and f.transform_version = s.transform_version
