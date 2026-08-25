-- docs/velocity_definitions.md rule 2 + Step 2 synthetic gap test.
-- Day 1 OK (U+V), no Day 2 rows, Day 3 OK (U+V still listed) must not
-- emit a lease. This is the test that keeps a failed scrape from looking
-- like rental velocity.

select e.*
from {{ ref('stg_lease_events') }} as e
inner join {{ ref('stg_facilities') }} as f
    on f.id = e.facility_id
where f.slug = 'gap-test'
