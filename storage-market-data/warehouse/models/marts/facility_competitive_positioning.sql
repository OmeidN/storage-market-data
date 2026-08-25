{{ config(materialized='table') }}

{# docs/velocity_definitions.md rule 5.
   Compare facilities inside the same market_name. Current 10 live
   facilities are one per city — singleton markets are expected.
   Velocity columns stay NULL when insufficient_history. #}

with latest_obs as (
    select
        u.facility_id,
        o.availability_status,
        o.standard_price, -- storage monthly asking (M6)
        o.scraped_at,
        row_number() over (
            partition by u.facility_id, u.id
            order by o.scraped_at desc
        ) as rn
    from {{ ref('stg_observations') }} as o
    inner join {{ ref('stg_units') }} as u
        on u.id = o.unit_id
),

latest as (
    select *
    from latest_obs
    where rn = 1
),

asking_stats as (
    select
        facility_id,
        count(*) as listed_unit_count,
        avg(standard_price) as avg_asking_price,
        sum(case when availability_status = 'AVAILABLE' then 1 else 0 end) as available_unit_count,
        sum(case when availability_status = 'SOLD_OUT' then 1 else 0 end) as sold_out_unit_count
    from latest
    group by facility_id
),

velocity as (
    select
        facility_id,
        max(case when confidence = 'confirmed' then avg_days_to_lease end) as avg_days_to_lease_confirmed,
        max(case when confidence = 'inferred' then avg_days_to_lease end) as avg_days_to_lease_inferred,
        max(case when confidence = 'confirmed' then insufficient_history end) as insufficient_history_confirmed,
        max(case when confidence = 'inferred' then insufficient_history end) as insufficient_history_inferred,
        max(snapshot_dates) as snapshot_dates
    from {{ ref('rental_velocity_by_facility') }}
    group by facility_id
)

select
    m.market_name,
    f.provider,
    f.slug,
    f.id as facility_id,
    a.listed_unit_count,
    a.avg_asking_price,
    a.available_unit_count,
    a.sold_out_unit_count,
    v.snapshot_dates,
    v.avg_days_to_lease_confirmed,
    v.insufficient_history_confirmed,
    v.avg_days_to_lease_inferred,
    v.insufficient_history_inferred
from {{ ref('stg_facilities') }} as f
left join {{ ref('stg_facility_market_map') }} as m
    on m.provider = f.provider
    and m.slug = f.slug
left join asking_stats as a
    on a.facility_id = f.id
left join velocity as v
    on v.facility_id = f.id
