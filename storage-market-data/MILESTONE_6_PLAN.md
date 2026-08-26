# Next Phase Plan — Milestone 6: Schema Generalization + Second Vertical

Builds on Milestones 1–5 (StorQuest pipeline, Postgres, Docker+CI, Cloud
Run + Scheduler for scrape and replication, BigQuery/dbt marts with a
correctly-gated rental velocity metric). Aligned to NORTH_STAR.md and
ROADMAP_M5_PLUS.md.

**Goal at the end of this phase:** the schema generalizes to a
`Listing`-shaped model that can hold both self-storage units and
warehouse/industrial spaces without either vertical faking fields it
doesn't have, one real warehouse/industrial provider is onboarded
end-to-end, and M5's marts (including rental velocity) still compute
correctly for StorQuest after the migration — no regression.

---

## Step 0 — Provider: ReadySpaces (vetted, decided)

**Provider:** `readyspaces.com` — 38 locations across the US and Canada,
small-format flex warehouse space (200–5,000 sq ft, size tiers rather
than exact dimensions).

**Vetting result:**
- `robots.txt`: fully open (`Disallow:` empty, stock Yoast default),
  sitemap available for facility discovery.
- No explicit anti-bot/scraper clause in terms of use (unlike a
  candidate we ruled out — WareSpace — which explicitly requires written
  permission for automated access).
- Standard "personal, non-commercial use" boilerplate is present, common
  to most commercial sites; accepted as background risk, not a blocker.

**Important limitation, decided:** ReadySpaces does **not** post real
per-listing prices. Their own FAQ and availability page explicitly say
pricing "varies" and to call/chat for an accurate number — the
$1,000–1,700/mo figures found in their marketing content are
illustrative averages, not structured per-facility data. **Decision:
onboard ReadySpaces for square footage, availability, and attributes
only. `price` is null for every ReadySpaces listing.** This still fully
supports rental velocity (which needs presence/absence, not price) but
means `price_history_by_market` will have no ReadySpaces rows this
milestone. See Step 1 and Step 3 for how this is modeled explicitly
rather than left as an ambiguous gap.

**Exit criteria:** met — provider chosen and vetted above.

---

## Step 1 — Design the generalized `Listing` model

**Build:**
- A `Listing` model (or generalized `Unit`) with universal fields:
  `square_footage`, `price`, `price_unit` (enum: e.g.
  `per_unit_per_month`, `per_sqft_per_year`, `per_sqft_per_month`),
  `availability_status`, `identity_key`.
- A flexible attributes structure (e.g. JSONB column) for
  vertical-specific fields: storage keeps `width_ft`/`length_ft`/
  `climate_controlled`/etc. inside it; warehouse gets `clear_height_ft`,
  `dock_doors`, etc. inside it.
- `asset_type`/`vertical` field on `Facility` (`self_storage`,
  `warehouse_industrial`, ...).
- A `price_data_available` boolean (or equivalent) on `Listing`,
  distinct from `price` itself being null. A null `price` should never
  be ambiguous between "we don't know" and "this provider doesn't
  publish it" — ReadySpaces listings set `price_data_available = false`
  explicitly, so downstream marts can distinguish a real data gap from
  an expected, permanent absence.
- An Alembic migration that **backfills existing StorQuest data into the
  new shape without data loss** — every existing observation must
  remain queryable, not just new data going forward.

**Test:**
- Post-migration, all pre-existing StorQuest facilities/units/
  observations are present with equivalent data (spot-check row counts
  and a few known values, e.g. Tracy's known unit set, before vs. after).
- A new warehouse-shaped listing (square footage, per-sqft-per-year
  price) validates correctly through the same Pydantic models that
  validate a storage unit — same model, different `price_unit` and
  attributes payload, not a parallel model.
- Existing model validation rules (missing price, missing size →
  `ValidationError`; failed scrape ≠ sold out) still hold for both
  verticals.

**Exit criteria:** the full M2–M5 test suite still passes against the
migrated schema, plus new tests proving a warehouse-shaped listing
round-trips correctly.

---

## Step 2 — Second-vertical collector + parser

**Build:**
- `app/providers/<chosen_provider>/parser.py`, following the same
  collector/parser separation as StorQuest — a plain HTTP collector
  first, browser fallback only if the site actually requires it.
- Real raw HTML fixtures saved and used for parser tests, same discipline
  as Milestone 2 Step 3 (no synthetic fixtures once real ones exist).

**Test:**
- Parser tests against real saved fixtures for at least a small number
  of real facilities (start small — 2–3 — not immediately 10).
- Spot-check at least one parsed facility against the live page by hand,
  same as was done for Anaheim/Arlington/Apopka in Milestone 2.

**Exit criteria:** at least 2–3 real warehouse/industrial facilities
collected, parsed, validated, and stored using the generalized model.

---

## Step 3 — Confirm marts still work across both verticals

**Build:**
- Update dbt staging/mart models so they operate on the universal
  `Listing` fields (`price`, `price_unit`, `square_footage`) rather than
  storage-specific ones. Storage-specific fields stay accessible via the
  attributes payload for storage-specific views, but the core marts
  (rental velocity, price comparison) should not require them.
- Re-run the M5 dbt test suite (`assert_gap_is_not_a_lease`, etc.)
  against the migrated schema.

**Test:**
- All M5 dbt tests still pass post-migration — this is a regression
  check, not new functionality.
- `rental_velocity_by_facility` still computes (or still correctly shows
  `insufficient_history`) for the existing StorQuest facilities after
  the migration — the numbers/gating state shouldn't change just because
  the schema did.
- A parallel velocity-style view exists conceptually for the new
  vertical, even if it's immediately gated as insufficient-history (which
  it will be, given no observation history exists yet for the new
  provider).
- `price_history_by_market` correctly shows zero rows for ReadySpaces
  facilities, with `price_data_available = false` visible rather than
  the facilities silently missing or looking like a bug.

**Exit criteria:** no regression in M5's marts or tests; the new
vertical's data is visible in the warehouse in the same shape, correctly
gated given its lack of history so far.

---

## Step 4 — LLM-extraction fallback (prototype only)

**Build:**
- A prototype: feed cleaned page text from ReadySpaces listing pages to
  **Gemini 2.5 Flash-Lite** (or its current-generation equivalent —
  verify the model hasn't been retired/replaced when this step is
  actually built), prompted to return structured JSON matching the
  `Listing` schema. Chosen specifically for minimal per-token cost
  ($0.10/$0.40 per million input/output tokens as of this writing,
  meaningfully cheaper than Claude's cheapest tier) — at this
  prototype's scale the absolute cost difference is trivial either way,
  but Gemini Flash-Lite is the right default given cost is the stated
  priority right now.
- Compare its output against the hand-written parser's output for the
  same fixtures from Step 2.

**Test:**
- Does the LLM extraction match the hand-written parser's output on the
  same fixtures? Where it disagrees, which one is actually correct
  against the live page?
- This is explicitly a prototype/comparison, not a replacement — the
  hand-written parser from Step 2 remains the production path unless
  this comparison clearly justifies switching.

**Exit criteria:** a documented comparison (accuracy, cost per page,
latency) between hand-written parsing and LLM extraction for this
provider — a decision, not necessarily a switch.

---

## Explicitly out of scope for this phase

- Client-facing comparison report (Milestone 7)
- A third vertical
- Facility-level scrape-outcome log (still deferred, per M5 Step 0 rule 3)
- Automated market/address parsing beyond the hand-seeded map (still
  fine to extend the seed file with the new facilities' markets, just
  no new parsing logic)
- Replacing the hand-written parser with the LLM fallback outright,
  unless Step 4's comparison clearly justifies it

---

## Ground rules (same as before)

- State what you're about to build and which files before writing code.
- The migration in Step 1 is the highest-risk part of this milestone —
  treat it with the same rigor as an M2-style "does this break existing
  history" check. Don't proceed to Step 2 until Step 1's regression
  tests pass.
- If the chosen provider turns out to need Playwright (JS-rendered
  pricing, not server-rendered like StorQuest), that's a legitimate,
  expected outcome — flag it and implement the fallback per planning.md's
  Playwright rules, don't force an HTTP-only approach that doesn't work.
