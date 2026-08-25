{{ config(materialized='view') }}

{# docs/velocity_definitions.md rules 1–2.
   confirmed = unit status becomes SOLD_OUT on consecutive unit observations.
   inferred = present on OK snapshot T, absent on the next OK snapshot T+1
   for that facility. Consecutive snapshots use LAG(scraped_at), never
   calendar DATE_ADD. days_to_lease is the listing-spell length (island). #}

with numbered_snapshots as (
    select
        facility_id,
        scraped_at,
        row_number() over (
            partition by facility_id
            order by scraped_at
        ) as snap_n
    from {{ ref('stg_facility_ok_snapshots') }}
),

presence as (
    select
        u.facility_id,
        o.unit_id,
        o.scraped_at,
        o.availability_status,
        ns.snap_n
    from {{ ref('stg_observations') }} as o
    inner join {{ ref('stg_units') }} as u
        on u.id = o.unit_id
    inner join numbered_snapshots as ns
        on ns.facility_id = u.facility_id
        and ns.scraped_at = o.scraped_at
),

islands as (
    select
        facility_id,
        unit_id,
        scraped_at,
        availability_status,
        snap_n,
        snap_n - row_number() over (
            partition by unit_id
            order by snap_n
        ) as island_id
    from presence
),

island_bounds as (
    select
        facility_id,
        unit_id,
        island_id,
        min(scraped_at) as spell_start,
        max(scraped_at) as spell_end
    from islands
    group by facility_id, unit_id, island_id
),

snapshot_pairs as (
    select
        facility_id,
        scraped_at,
        lag(scraped_at) over (
            partition by facility_id
            order by scraped_at
        ) as prev_scraped_at
    from {{ ref('stg_facility_ok_snapshots') }}
),

inferred as (
    select
        s.facility_id,
        p.unit_id,
        s.scraped_at as leased_at,
        ib.spell_start,
        'inferred' as confidence
    from snapshot_pairs as s
    inner join presence as p
        on p.facility_id = s.facility_id
        and p.scraped_at = s.prev_scraped_at
    inner join island_bounds as ib
        on ib.unit_id = p.unit_id
        and ib.spell_end = s.prev_scraped_at
    where s.prev_scraped_at is not null
      and not exists (
          select 1
          from presence as c
          where c.unit_id = p.unit_id
            and c.scraped_at = s.scraped_at
      )
),

unit_obs_seq as (
    select
        u.facility_id,
        o.unit_id,
        o.scraped_at,
        o.availability_status,
        lag(o.availability_status) over (
            partition by o.unit_id
            order by o.scraped_at
        ) as prev_status
    from {{ ref('stg_observations') }} as o
    inner join {{ ref('stg_units') }} as u
        on u.id = o.unit_id
),

confirmed as (
    select
        seq.facility_id,
        seq.unit_id,
        seq.scraped_at as leased_at,
        ib.spell_start,
        'confirmed' as confidence
    from unit_obs_seq as seq
    inner join island_bounds as ib
        on ib.unit_id = seq.unit_id
        and ib.spell_end >= seq.scraped_at
        and ib.spell_start <= seq.scraped_at
    where seq.availability_status = 'SOLD_OUT'
      and seq.prev_status is not null
      and seq.prev_status != 'SOLD_OUT'
)

select
    facility_id,
    unit_id,
    leased_at,
    spell_start,
    {{ days_between('leased_at', 'spell_start') }} as days_to_lease,
    confidence
from confirmed

union all

select
    facility_id,
    unit_id,
    leased_at,
    spell_start,
    {{ days_between('leased_at', 'spell_start') }} as days_to_lease,
    confidence
from inferred
