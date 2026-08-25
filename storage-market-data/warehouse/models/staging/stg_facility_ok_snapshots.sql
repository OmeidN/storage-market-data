{{ config(materialized='view') }}

{# docs/velocity_definitions.md rule 2:
   An OK snapshot is any (facility_id, scraped_at) with ≥1 observation.
   Calendar gaps are not snapshots. #}

select distinct
    u.facility_id,
    o.scraped_at
from {{ ref('stg_observations') }} as o
inner join {{ ref('stg_units') }} as u
    on u.id = o.unit_id
