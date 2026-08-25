# Milestone 5 — Warehouse and comparison metrics

**Status:** closed  
**Commit:** `991583c`  
**CI:** [actions/runs/32897848400](https://github.com/OmeidN/storage-market-data/actions/runs/32897848400) — **test** and **dbt** both success

---

## What was created, and why

Milestones 1–4 collect honest snapshots. Milestone 5 is the first **analytics layer**: copy that history into BigQuery, transform it with dbt into comparison marts, and look at it internally in Looker Studio.

The flagship metric is **average days-to-lease** (rental velocity). Competitors’ listing sites cannot produce it; it requires the append-only store from M2 and the daily job from M4. The risk is computing a fake number from scrape gaps. Definitions were written **before** SQL (`docs/velocity_definitions.md`):

- **Confirmed** lease: `availability_status` → `SOLD_OUT` between consecutive observations of that unit.
- **Inferred** lease: present on facility OK snapshot T, absent on the next OK snapshot **for that facility** (`LAG` on timestamps — never calendar days).
- A scrape gap is not a lease. `NO_UNITS` (successful empty scrape) is a known hole; no schema fix in M5.
- Velocity is **gated**: `insufficient_history` unless ≥14 snapshot dates **and** ≥2 events in that confidence tier; then `avg_days_to_lease` is NULL.
- Markets: hand-built `warehouse/seeds/facility_market_map.csv` by `provider` + `slug`.
- `width_ft` / `length_ft` / monthly unit price are storage-specific; generalize in M6.

**What shipped:**

- `scripts/replicate_to_bigquery.py` — truncate-reload of `facilities`, `units`, `observations` into `storage_market_data_raw`.
- Cloud Run Job `replicate-to-bigquery` (image `…/replicate:latest`), schedule **`30 6 * * *` PT** (after the 06:00 scrape). SA `replicate-job@`. Does **not** modify the scrape job.
- dbt `warehouse/`: DuckDB `ci` target + BigQuery `prod`. Staging (OK snapshots, lease events with `confidence`) and marts `rental_velocity_by_facility`, `price_history_by_market`, `facility_competitive_positioning` in `storage_market_data_marts`.
- GitHub Actions **dbt** job: seed → run → test on DuckDB (no Supabase).
- Internal Looker Studio notes: `docs/looker_studio_internal.md`. Not a client report.

## What was tested, and the results

**dbt (CI / DuckDB), including the load-bearing gap test:**

| Test | Intent | Result |
|---|---|---|
| `assert_gap_is_not_a_lease` | Synthetic missing day must not emit a lease | Pass |
| `assert_confirmed_lease_emitted` / `assert_inferred_lease_emitted` | Both tiers exist when the fixture warrants them | Pass |
| `assert_confirmed_vs_inferred_distinct` | Tiers are not blended | Pass |
| `assert_gated_velocity_is_null` | Too little history → NULL average, flag on | Pass |
| `assert_ungated_confirmed_average` | Enough confirmed history → a real number | Pass |

**Replication / cloud job:**

- Local truncate-reload proven with matching row counts (idempotent).
- Unattended Scheduler (same bar as M4): four successes **RUN BY** `scrape-scheduler@…`, created 13:30 UTC = **06:30 PT** — `flkgd` (Aug 22), `z2npz` (Aug 23), `4w728` (Aug 24), `lvz7f` (Aug 25, 1m7s, `succeededCount: 1`). Manual-only run was `z57b8` on Aug 21.

**CI on the M5 push:**

- Workflow: [32897848400](https://github.com/OmeidN/storage-market-data/actions/runs/32897848400)
- [test](https://github.com/OmeidN/storage-market-data/actions/runs/32897848400/job/97964508206) — success  
- [dbt](https://github.com/OmeidN/storage-market-data/actions/runs/32897848400/job/97964508398) — success  

**Looker (internal, Aug 25):** 20 rows (10 facilities × 2 confidence tiers). All `insufficient_history = true`, `avg_days_to_lease` null, `snapshot_dates = 5`, some `lease_event_count` 0–4. That is **correct**: daily collection had not yet reached 14 dates and 2 events per tier. The gate is doing its job; this is not a client velocity number.

## How this contributes to the bigger picture

This is the first time the project produces **comparison-shaped tables** instead of only raw observations. Acquisition teams should eventually read “Property A rents in 9 days vs 40 down the street” — M5 is the pipe and the honesty rules for that sentence, not the sentence itself.

What this milestone deliberately is not:

- **M6** — second vertical (warehouse/industrial) and a generalized listing model.
- **M7** — the actual product: a static comparison report / PDF with an LLM narrative, scoped as asking-side intelligence only.
- **M8** — interactive dashboard, after the static report is proven.

Postgres remains the system of record. The warehouse reads it. A NULL velocity today is a successful milestone; a made-up average would have been a failure.
