with fixture_counts as (
    select count(*) as fixtures,
           sum(case when status = 'completed' then 1 else 0 end) as completed,
           sum(case when status = 'result_unavailable' then 1 else 0 end) as without_result
    from {{ ref('fixture_schedule') }}
), fact_counts as (
    select count(*) as matches from {{ ref('fact_match') }}
)
select * from fixture_counts cross join fact_counts
where fixtures != completed + without_result or matches != completed
