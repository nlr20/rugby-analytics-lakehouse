with names as (
    select home_team as team_name from {{ ref('stg_latest_matches') }}
    union
    select away_team as team_name from {{ ref('stg_latest_matches') }}
)
select sha2(team_name, 256) as team_id, team_name from names

