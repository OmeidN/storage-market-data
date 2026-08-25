-- docs/velocity_definitions.md rule 1: inferred vs confirmed stay separate.
-- inferred-test must emit inferred only; confirmed-test confirmed only.

select e.*
from {{ ref('stg_lease_events') }} as e
inner join {{ ref('stg_facilities') }} as f
    on f.id = e.facility_id
where (f.slug = 'inferred-test' and e.confidence != 'inferred')
   or (f.slug = 'confirmed-test' and e.confidence != 'confirmed')
   or (f.slug = 'inferred-test' and e.confidence is null)
