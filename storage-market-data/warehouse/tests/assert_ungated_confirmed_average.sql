-- Synthetic ungated facility (14 snapshot days, 2 confirmed leases)
-- must produce a non-null confirmed average. Spot-check vs raw:
-- unit-a spell 1 Jan -> 6 Jan = 5 days; unit-b 1 Jan -> 14 Jan = 13 days;
-- average 9.

select v.*
from {{ ref('rental_velocity_by_facility') }} as v
inner join {{ ref('stg_facilities') }} as f
    on f.id = v.facility_id
where f.slug = 'ungated-test'
  and v.confidence = 'confirmed'
  and (
      v.insufficient_history = true
      or v.avg_days_to_lease is null
      or v.avg_days_to_lease != 9
      or v.lease_event_count != 2
  )
