# Next Phase Plan — Milestone 5: Warehouse + Comparison Metrics

Builds on Milestones 1–4 (StorQuest parser/models/Postgres, Docker+CI,
Cloud Run + daily Scheduler). Aligned to NORTH_STAR.md and
ROADMAP_M5_PLUS.md. Does not touch the parser, models, schema, Docker
setup, or Cloud Run deployment — this phase reads from Postgres, it
doesn't change how data gets into it.

**Goal at the end of this phase:** BigQuery holds replicated observation
history, dbt transforms it into comparison-ready marts (including a
correctly-gated rental velocity metric), and Looker/Tableau can query
those marts for internal exploration.

---

## Step 0 — Write down the definitions, before building anything

These are the answers to the six questions from Cursor's review. Put
this as a short doc (`docs/velocity_definitions.md` or similar) that the
dbt models can reference in comments, so the rules live somewhere
explicit, not only in someone's head:

1. **"Leased" signal, two tiers:**
   - **High-confidence:** a unit's `availability_status` transitions to
     `SOLD_OUT` between two consecutive observations.
   - **Inferred:** a unit present in one facility-level `OK` snapshot is
     absent in the next facility-level `OK` snapshot. Mark these rows
     `confidence = inferred` vs `confidence = confirmed` — don't blend
     them into one undifferentiated average.
2. **Facility-level "had a successful scrape" signal:** reconstructed in
   staging by grouping observations on `(facility_id, scraped_at)` — if
   any unit at a facility has an observation at a given `scraped_at`,
   that facility had an `OK` snapshot at that timestamp. A calendar gap
   (including one facility failing while nine others succeed) must not
   be treated as evidence a unit leased — only compare consecutive
   *actual* `OK` snapshots for that facility, never consecutive calendar
   days blindly.
3. **Known hole, accepted for M5:** a successful scrape that legitimately
   finds zero units (`NO_UNITS`, nothing persisted) can't be
   distinguished from "we don't know." This means a facility-wide sellout
   can't currently close out remaining units in the warehouse. Document
   this as a limitation; do not attempt a schema fix in this milestone —
   a facility-level scrape-outcome log is a future, separate addition.
4. **Minimum history threshold:** define a per-facility minimum
   observation count/time span (e.g. at least 2 confirmed lease events,
   or N days of daily snapshots) below which velocity output is flagged
   `insufficient_history = true` rather than shown as a number. Given
   daily collection just started, expect most/all facilities to be below
   this threshold for several weeks — that's expected, not a bug.
5. **Market definition:** a small hand-built seed file
   (`seeds/facility_market_map.csv` or equivalent) mapping each of the 10
   known facility IDs to a market name. No address-parsing logic in this
   milestone.
6. **Vertical-specific fields stay labeled as such.** Any dbt model
   referencing `width_ft`/`length_ft`/per-unit-monthly pricing should
   have a comment noting these are storage-specific and will need
   generalizing in Milestone 6 — don't let mart logic quietly assume
   these are universal.

**Test:** none — this is a documentation step. Exit criteria: the doc
exists and Steps 1–4 below explicitly reference it rather than
re-deriving these rules ad hoc in code.

---

## Step 1 — Batch replication: Postgres → BigQuery

**Build:**
- A batch job (can be a simple scheduled script for now — not a new
  Cloud Run Job/Scheduler pair unless that's clearly easier) that copies
  `facilities`, `units`, `observations` from Supabase Postgres into
  BigQuery on some cadence (daily, after the scrape, is reasonable).
- Raw tables in BigQuery should mirror Postgres structure — no
  transformation at this stage, that's dbt's job next.

**Test:**
- Row counts in BigQuery match Postgres for all three tables after a
  run.
- Running the replication twice doesn't duplicate rows (idempotent load,
  e.g. truncate-and-reload or a merge on primary key).

**Exit criteria:** BigQuery's raw tables are a faithful, non-duplicated
copy of Postgres as of the last replication run.

---

## Step 2 — dbt staging layer

**Build:**
- Staging models cleaning/typing the raw replicated tables.
- The facility-level `OK` snapshot reconstruction from Step 0, rule 2 —
  this is the load-bearing piece everything else depends on.
- A `confidence` field per inferred-lease event per Step 0, rule 1.

**Test:**
- dbt tests confirming no staging model treats a scrape gap as a lease
  event (a synthetic test case: one facility with a deliberate missing
  day in its observation history should not produce a false lease
  signal for that gap).
- Confirmed vs. inferred lease events are distinguishable in the output,
  not merged.

**Exit criteria:** staging models pass their dbt tests, including the
synthetic gap-doesn't-mean-leased test.

---

## Step 3 — dbt marts

**Build:**
- `rental_velocity_by_facility` — average days-to-lease per facility,
  split by confidence tier, gated by the minimum-history threshold from
  Step 0 rule 4 (`insufficient_history` flag where applicable).
- `price_history_by_market` — using the hand-mapped seed file from Step
  0 rule 5.
- `facility_competitive_positioning` — as originally scoped, comparing
  facilities within the same market.

**Test:**
- A facility with too little history shows `insufficient_history = true`
  and no misleadingly precise velocity number.
- A facility with enough confirmed history produces a plausible number,
  spot-checked by hand against the raw observation data for at least one
  facility.

**Exit criteria:** all three marts build successfully; the
insufficient-history gating is visibly working, not just implemented.

---

## Step 4 — Looker/Tableau connection (internal only)

**Build:**
- Connect Looker or Tableau to the dbt marts for your own exploration —
  this is explicitly not the client-facing report yet (that's
  Milestone 7).

**Test:**
- You can manually pull up rental velocity and price history for the 10
  known facilities and the numbers match what the marts produced.

**Exit criteria:** you can look at the 10 facilities side by side in
Looker/Tableau and the insufficient-history facilities are visibly
marked as such, not silently showing a number.

---

## Explicitly out of scope for this phase

- Client-facing report generation (Milestone 7)
- Second vertical / `Listing` model generalization (Milestone 6)
- Facility-level scrape-outcome log (a real future schema addition, not
  this milestone)
- Automated market/address parsing (deferred per Step 0 rule 5)
- Any change to the parser, Pydantic models, Postgres schema, Docker, or
  Cloud Run/Scheduler config

---

## Ground rules (same as before)

- State what you're about to build and which files before writing code.
- If real replicated data reveals the Step 0 definitions were wrong in
  some way (e.g. the facility-level `OK` grouping doesn't hold up), stop
  and flag it rather than quietly patching around it — these definitions
  are load-bearing for a metric the whole product concept depends on.
- Given daily cadence just started, don't expect meaningful velocity
  numbers yet — this milestone is "the pipe is built and gated
  correctly," not "the numbers are already trustworthy."
