-- inferred-test: unit U gone on the next OK snapshot while V remains.
select 1
from {{ ref('stg_facilities') }} as f
left join {{ ref('stg_lease_events') }} as e
    on e.facility_id = f.id
    and e.confidence = 'inferred'
where f.slug = 'inferred-test'
group by f.id
having count(e.unit_id) != 1
