-- confirmed-test: AVAILABLE -> SOLD_OUT emits exactly one confirmed event.
select 1
from {{ ref('stg_facilities') }} as f
left join {{ ref('stg_lease_events') }} as e
    on e.facility_id = f.id
    and e.confidence = 'confirmed'
where f.slug = 'confirmed-test'
group by f.id
having count(e.unit_id) != 1
