# storage-market-data

Market intelligence for self-storage and small warehouse/industrial
properties, built from publicly listed pricing and availability.

A daily job scrapes a hand-picked set of facility pages, validates every
listing, and appends it to Postgres as an observation that is never
overwritten. A second daily job copies that history into BigQuery, where
dbt builds comparison marts. The flagship metric is **rental velocity**
(average days-to-lease): how fast units at a property actually rent,
inferred from watching listings appear and disappear over time. It is
gated until enough history exists, and a failed scrape or a gap in
collection is never counted as a lease.

The goal is a decision-support tool for acquisition teams. It covers the
asking side only: price, availability, and lease-up speed. It does not
cover underwriting data such as cap rates or NOI. See
[NORTH_STAR.md](storage-market-data/NORTH_STAR.md).

## Where things are

- [storage-market-data/README.md](storage-market-data/README.md): setup, Docker, cloud deployment, warehouse, CI
- [ROADMAP_M5_PLUS.md](storage-market-data/ROADMAP_M5_PLUS.md): milestone roadmap
- [docs/velocity_definitions.md](storage-market-data/docs/velocity_definitions.md): the rules behind rental velocity
- `storage-market-data/MILESTONE_N_PLAN.md`: the plan written before each milestone

## Milestone journals

| # | Milestone |
|---|---|
| 1 | [One provider, one real facility](journal/milestone-1.md) |
| 2 | [Validated history in Postgres, ten facilities](journal/milestone-2.md) |
| 3 | [Docker + CI](journal/milestone-3.md) |
| 4 | [Unattended scrape in GCP](journal/milestone-4.md) |
| 5 | [Warehouse and comparison metrics](journal/milestone-5.md) |
| 6 | [Second vertical and a generalized listing model](journal/milestone-6.md) |

Next: Milestone 7, the first static comparison report.

Stack: Python, Pydantic, SQLAlchemy/Alembic, Postgres (Supabase), Cloud Run
Jobs + Cloud Scheduler, BigQuery, dbt, GitHub Actions.
