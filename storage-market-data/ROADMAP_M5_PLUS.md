# Roadmap — Milestone 5 onward (revised)

Milestones 1–4 are built as planned (parser/models/Postgres, Docker+CI,
Cloud Run+Scheduler) and are unaffected by this revision. This document
replaces the vague later-phase language in the original `planning.md`
with a roadmap aligned to `NORTH_STAR.md`.

---

## Milestone 5 — Warehouse + comparison metrics layer

Originally scoped as "BigQuery/Snowflake + dbt + BI," now sharpened
around the flagship metric.

- Batch-replicate Postgres observations into BigQuery or Snowflake.
- dbt staging layer: clean, typed observation history.
- dbt marts, explicitly built around comparison, not just normalization:
  - `rental_velocity_by_facility` — average days-to-lease per facility,
    derived from unit presence/absence across observation snapshots.
  - `price_history_by_market` — as originally planned.
  - `facility_competitive_positioning` — as originally planned.
- Looker/Tableau on top — first as an internal exploration tool for you,
  not yet the client-facing report.

**Note carried forward from Milestone 2 feedback:** a unit disappearing
from a listing needs to be distinguishable from "not observed this run"
before rental velocity can be trusted. This is where that distinction
finally gets resolved — likely as an explicit `last_seen_at` /
`inferred_leased_at` field in the staging model.

## Milestone 6 — Second vertical (warehouse/industrial) + data model generalization

Replaces "onboard a second self-storage provider" — a second vertical is
more valuable than a second storage-unit site, since it forces the
schema to actually generalize.

- Generalize `Unit`/`Facility` toward a `Listing` model: universal fields
  (square footage, price, price unit — per-sqft/year vs per-unit/month —
  availability) plus a flexible attributes structure for vertical-specific
  fields (clear height, dock doors for warehouse; climate control,
  drive-up access for storage).
- Add a `vertical`/`asset_type` field to `Facility`.
- Onboard one real warehouse/industrial listing site, following the same
  provider-onboarding policy (robots.txt/ToS check first) as StorQuest.
- Prototype the LLM-extraction fallback here, where a second, differently
  structured site makes a hand-written parser meaningfully more
  expensive than trying LLM-based structured extraction.

## Milestone 7 — First generated comparison report (static)

The first version of the actual product.

- Given 2+ properties (within one vertical to start), generate a static
  report: a comparison table (price, availability, size, rental
  velocity) plus an LLM-written narrative summary.
- Narrative generation should be explicit about the asking-side/
  underwriting-side scope boundary from `NORTH_STAR.md` — no implied
  investment recommendation beyond what the data supports.
- Output as PDF or similar static document — not a dashboard yet.

## Milestone 8 — Interactive dashboard

- Take the report format from Milestone 7 and make it browsable/
  interactive, once the static format has been validated with real
  comparisons.

## Later — Cloud Composer, geographic/vertical scaling

Unchanged from earlier discussion: Composer gets introduced once there's
real multi-provider/multi-vertical dependency logic worth orchestrating,
not before.

---

## Explicitly deferred, not abandoned

- Third+ verticals (office, retail, coworking) — after Milestone 6 proves
  the two-vertical model works.
- Unit-level (not just property-level) comparison — secondary lens per
  `NORTH_STAR.md`, after property-level comparison is solid.
