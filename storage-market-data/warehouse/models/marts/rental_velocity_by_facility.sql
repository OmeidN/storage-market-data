{{ config(materialized='table') }}

{# docs/velocity_definitions.md rule 4.
   Split by confidence; do not blend. NULL average when gated.
   insufficient_history unless snapshot_dates >= 14 AND events in
   this tier >= 2. Live data will be gated for weeks — that is success. #}

with snapshot_days as (
    select
        facility_id,
        count(distinct {% if target.type == 'bigquery' %}
            date(scraped_at)
        {% else %}
            scraped_at::date
        {% endif %}) as snapshot_dates
    from {{ ref('stg_facility_ok_snapshots') }}
    group by facility_id
),

tiers as (
    select 'confirmed' as confidence
    union all
    select 'inferred' as confidence
),

facility_tiers as (
    select
        f.id as facility_id,
        f.provider,
        f.slug,
        m.market_name,
        t.confidence,
        coalesce(sd.snapshot_dates, 0) as snapshot_dates
    from {{ ref('stg_facilities') }} as f
    cross join tiers as t
    left join snapshot_days as sd
        on sd.facility_id = f.id
    left join {{ ref('stg_facility_market_map') }} as m
        on m.provider = f.provider
        and m.slug = f.slug
),

event_stats as (
    select
        facility_id,
        confidence,
        count(*) as lease_event_count,
        avg(days_to_lease) as avg_days_to_lease
    from {{ ref('stg_lease_events') }}
    group by facility_id, confidence
)

select
    ft.facility_id,
    ft.provider,
    ft.slug,
    ft.market_name,
    ft.confidence,
    ft.snapshot_dates,
    coalesce(es.lease_event_count, 0) as lease_event_count,
    case
        when ft.snapshot_dates >= 14
            and coalesce(es.lease_event_count, 0) >= 2
            then es.avg_days_to_lease
        else null
    end as avg_days_to_lease,
    case
        when ft.snapshot_dates >= 14
            and coalesce(es.lease_event_count, 0) >= 2
            then false
        else true
    end as insufficient_history
from facility_tiers as ft
left join event_stats as es
    on es.facility_id = ft.facility_id
    and es.confidence = ft.confidence
