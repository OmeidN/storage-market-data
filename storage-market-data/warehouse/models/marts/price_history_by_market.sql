{{ config(materialized='table') }}

{# docs/velocity_definitions.md rules 5–6.
   Market comes from the hand-built seed (provider+slug), not address
   parsing. width_ft / length_ft / monthly prices are storage-specific
   (Milestone 6). #}

select
    m.market_name,
    f.provider,
    f.slug,
    f.id as facility_id,
    u.id as unit_id,
    u.identity_key,
    u.width_ft,          -- storage-specific (M6)
    u.length_ft,         -- storage-specific (M6)
    o.scraped_at,
    o.standard_price,    -- storage monthly asking (M6)
    o.promo_price,       -- storage monthly asking (M6)
    o.availability_status
from {{ ref('stg_observations') }} as o
inner join {{ ref('stg_units') }} as u
    on u.id = o.unit_id
inner join {{ ref('stg_facilities') }} as f
    on f.id = u.facility_id
left join {{ ref('stg_facility_market_map') }} as m
    on m.provider = f.provider
    and m.slug = f.slug
