{{ config(materialized='table') }}

{# docs/velocity_definitions.md rules 5–6.
   Market comes from the hand-built seed (provider+slug).
   Only rows where the provider publishes price. ReadySpaces is excluded
   because price_data_available is false — not a silent $0. #}

select
    m.market_name,
    f.provider,
    f.slug,
    f.id as facility_id,
    f.asset_type,
    u.id as unit_id,
    u.identity_key,
    u.square_footage,
    o.scraped_at,
    o.price,
    o.price_unit,
    o.price_data_available,
    o.availability_status
from {{ ref('stg_observations') }} as o
inner join {{ ref('stg_units') }} as u
    on u.id = o.unit_id
inner join {{ ref('stg_facilities') }} as f
    on f.id = u.facility_id
left join {{ ref('stg_facility_market_map') }} as m
    on m.provider = f.provider
    and m.slug = f.slug
where o.price_data_available
