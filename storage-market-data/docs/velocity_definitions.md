# Rental velocity definitions (Milestone 5)

Load-bearing rules for dbt staging and marts. Cite this file from model
headers. Do not re-derive these in SQL comments as if they were new.

Postgres remains the system of record. A failed scrape never writes
observations (`save_observation` no-ops on `FAILED` / `NO_UNITS`).
Warehouse logic must not invent a lease from a calendar hole.

---

## Rule 1 — Two "leased" tiers (never blended)

**`confirmed`:** the same unit's `availability_status` becomes `SOLD_OUT`
between two consecutive *observations of that unit* (previous status is
not `SOLD_OUT`). Seeing `SOLD_OUT` on a successful scrape is a real
listing signal, not a scrape failure.

**`inferred`:** the unit is present in facility-level OK snapshot T and
absent in the next facility-level OK snapshot T+1. Mark
`confidence = inferred`.

Do not average confirmed and inferred days-to-lease together.

**`days_to_lease`:** duration of the listing *spell* that ends at the
lease event — from the first OK snapshot in the contiguous presence
island through the triggering snapshot — not "one day since last seen."
That is what can read as "9 days vs 40 days."

---

## Rule 2 — Facility-level OK snapshot

An OK snapshot is any `(facility_id, scraped_at)` that has **at least
one** observation. Reconstruct in staging by grouping observations.

Lease inference compares consecutive **actual** OK snapshots for **that
facility** (`LAG` on snapshot timestamps). Never `DATE_ADD` calendar
days. A gap (including one facility failing while the other nine
succeed) is not evidence a unit leased.

---

## Rule 3 — Known hole (accepted in M5)

A successful scrape that finds zero units (`NO_UNITS`) persists nothing,
so it cannot be distinguished from "we don't know." A facility-wide
empty listing cannot close out remaining units in the warehouse. Do not
add a scrape-outcome table in this milestone.

---

## Rule 4 — Insufficient-history gate

Per facility **and** confidence tier:

`insufficient_history = true` unless **both**:

- distinct OK snapshot **dates** ≥ 14, and
- lease events in **that** confidence tier ≥ 2

When gated, `avg_days_to_lease` is **NULL** (not 0, not a one-event
number). Daily collection just started; expect all live facilities to
be gated for weeks. That is correct.

---

## Rule 5 — Market

Hand-built seed `warehouse/seeds/facility_market_map.csv`, keyed by
`provider` + `slug` (not integer `facility_id`). No address parsing.
The current 10 facilities are one per city; competitive-positioning
markets will mostly be singletons until more facilities exist. Do not
merge states to fake a competitive set.

---

## Rule 6 — Storage-specific columns

`width_ft`, `length_ft`, and per-unit monthly prices are self-storage
shapes. Any dbt model that selects them must comment that they
generalize in Milestone 6. Do not treat them as universal listing
fields.
