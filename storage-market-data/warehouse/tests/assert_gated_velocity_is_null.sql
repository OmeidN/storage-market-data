-- docs/velocity_definitions.md rule 4.
-- Too little history: insufficient_history = true and avg is NULL.

select v.*
from {{ ref('rental_velocity_by_facility') }} as v
inner join {{ ref('stg_facilities') }} as f
    on f.id = v.facility_id
where f.slug = 'gated-test'
  and (
      v.insufficient_history = false
      or v.avg_days_to_lease is not null
  )
