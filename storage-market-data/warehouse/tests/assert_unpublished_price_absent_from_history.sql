-- docs/velocity_definitions.md rule 6.
-- Providers that never publish price must not appear in price history
-- as $0 rows. The CI seed facility rs-noprice is price_data_available=false.

select h.*
from {{ ref('price_history_by_market') }} as h
where h.slug = 'rs-noprice'
