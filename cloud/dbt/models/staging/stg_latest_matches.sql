{{ config(materialized='view') }}

with ranked as (
    select *, row_number() over (
        partition by match_id order by ingested_at desc, transform_version desc, source_hash desc
    ) as version_rank
    from {{ source('silver', 'silver_match_versions') }}
)
select * except (version_rank)
from ranked
where version_rank = 1

