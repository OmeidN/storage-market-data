# Next Phase Plan — Milestone 7: First Static Comparison Report

> **Draft for review.** Decisions marked _OPEN_ need an answer before
> Step 1 starts.

Builds on Milestones 1–6 (StorQuest + ReadySpaces pipelines, append-only
Postgres history, Docker+CI, Cloud Run scrape and replication jobs,
BigQuery/dbt marts with gated rental velocity, generalized `Listing`
model). Aligned to NORTH_STAR.md and ROADMAP_M5_PLUS.md. Does not change
the scrapers, the schema, or the cloud jobs. This phase reads the marts
and produces a document. It doesn't change how data gets in.

**Goal at the end of this phase:** given 2+ facilities in one vertical,
a single command produces a static report (PDF): a comparison table
(price, availability, size, rental velocity) plus a short LLM-written
narrative. Every number in the narrative comes from the table. The
narrative is worded as asking-side intelligence only, and velocity that
is still gated is reported as "insufficient history", never as a number.

---

## Step 0 — Decide the report contract, before building anything

Write these down in a short doc (`docs/report_definitions.md` or
similar), the same way `velocity_definitions.md` came before M5's SQL:

1. **Comparison set is explicit.** The caller names the facilities
   (`provider` + `slug`), 2 or more, all with the same `asset_type`.
   Mixed verticals are rejected, not silently compared. Today's markets
   are one facility per city (singleton markets in
   `facility_market_map.csv`). The report must not call a hand-picked
   set a "market" or a "competitive set" unless the seed says so.
2. **Source of numbers.** The report reads one mart,
   `facility_competitive_positioning`, plus `rental_velocity_by_facility`
   for tier detail. No new metric logic in Python. If a number is
   missing from the marts, add it in dbt with a test, not in the report
   code.
3. **Gated velocity is shown as gated.** When `insufficient_history` is
   true for a tier, the table shows "Insufficient history (N snapshot
   days, M events)" and the narrative says that velocity can't be
   compared yet. Confirmed and inferred are never blended, and
   ReadySpaces is labelled inferred-only.
4. **Unpublished price is shown as unpublished.** `price_data_available
   = false` renders as "Not published by provider", never $0 or blank.
   `price_unit` is shown with every price, and prices with different
   units are not compared directly.
5. **Narrative scope boundary** (from NORTH_STAR.md): describe how the
   properties compare on publicly observed price, availability, size,
   and lease-up speed. No buy/sell/invest recommendation, no cap rate,
   NOI, valuation, or demand forecast, and no claim the data doesn't
   support. A fixed disclaimer line states the asking-side scope.
6. **Narrative LLM** — _OPEN:_ Gemini Flash-Lite, for consistency with
   M6's cost priority, or another model. Verify the model id is current
   when this step is built. The key comes from the environment only and
   is never in git or CI.
7. **Output format** — _OPEN:_ HTML template rendered to PDF. Suggested
   route: a Jinja2 HTML template printed to PDF with Playwright
   (`page.pdf`). That reuses the existing optional `[browser]` extra
   instead of adding WeasyPrint, which needs GTK on Windows.
8. **Data source for real runs** — _OPEN:_ read the prod BigQuery marts
   (needs ADC, and must be run deliberately, never from CI), or export
   them to a local file first. Development and CI use the DuckDB `ci`
   target only.

**Test:** none. This is a documentation step.

**Exit criteria:** the doc exists, the _OPEN_ items are decided, and
Step 1 can cite it.

---

## Step 1 — Comparison dataset

**Build:**
- A small module (e.g. `app/reports/dataset.py`) that takes a list of
  `provider` + `slug` and returns one typed row per facility (Pydantic),
  read from the marts. Fields: name/address, asset type, listed and
  available unit counts, square-footage range, asking price summary with
  `price_unit` and `price_data_available`, snapshot days, and velocity
  per tier with its `insufficient_history` flag.
- Validation: fewer than 2 facilities, unknown slugs, or mixed
  `asset_type` raise clear errors.

**Test (DuckDB ci seeds, no network):**
- A gated facility comes back with a NULL velocity and the flag set,
  never 0.
- The CI no-price facility (`rs-noprice`) comes back with
  `price_data_available = false` and no price.
- A mixed-vertical request is rejected.

**Exit criteria:** the dataset for a ci-seed comparison is built and
asserted in pytest, with no live database or cloud access.

---

## Step 2 — Comparison table

**Build:**
- An HTML template that renders the dataset as a comparison table,
  following Step 0 rules 3–4 for gated velocity, unpublished prices, and
  price units. Include a "data as of" line (latest snapshot date per
  facility) and the snapshot-day count.

**Test:**
- Snapshot-style tests on the rendered HTML: "Insufficient history"
  appears where velocity is gated, "Not published by provider" appears
  for ReadySpaces-style rows, and no `$0` appears for an unpublished
  price.

**Exit criteria:** the table renders correctly for both a StorQuest-only
and a ReadySpaces-only comparison from the ci seeds.

---

## Step 3 — LLM narrative

**Build:**
- A prompt that receives only the structured dataset (not raw pages or
  the database) and returns a short narrative (around 3 paragraphs)
  under the Step 0 rule 5 scope.
- A **grounding check** after generation: every number in the narrative
  must appear in the dataset, with rounding allowed. Any banned framing
  (buy/sell/invest/recommend, cap rate, NOI, valuation) fails the check.
  On failure, retry once, then fall back to a table-only report that
  says "Narrative unavailable". Never publish an ungrounded narrative.

**Test:**
- The grounding check is unit-tested with canned narratives (a good one,
  an invented number, a "strong buy" phrase, a velocity number for a
  gated facility). No API call in tests or CI.
- One manual run against real Gemini for a ci-seed comparison, with the
  result recorded in the journal.

**Exit criteria:** the grounding check rejects every bad case. One real
narrative passes it and reads as asking-side only.

---

## Step 4 — Static PDF + CLI

**Build:**
- `scripts/generate_report.py --facilities provider:slug,provider:slug
  [--out reports/...pdf] [--no-narrative]` combines the table, the
  narrative, and the disclaimer into a PDF via the Step 0 rule 7 route.
- Generated reports go to a gitignored output directory.

**Test:**
- The CLI runs end-to-end on the ci seeds with `--no-narrative`, and the
  PDF exists and is non-empty.
- One real comparison (_OPEN:_ which facilities, e.g. two StorQuest
  facilities with the most snapshot days) generated by hand, read
  start to finish, and checked against the marts.

**Exit criteria:** one real PDF report exists for 2+ facilities in one
vertical, its numbers match the marts, and the gating and price rules
are visibly respected.

---

## Explicitly out of scope for this phase

- Interactive dashboard or web UI (Milestone 8)
- Unit-level comparison (all 10×10s, all >5,000 sq ft spaces), the
  secondary lens after property-level comparison works
- Cross-vertical comparisons (storage vs warehouse in one report)
- New providers, a third vertical, or facility discovery
- Scheduled or automated report generation, emailing or hosting reports
- Any change to velocity definitions or gating thresholds to make the
  report "show a number"
- Underwriting-side data of any kind (cap rates, NOI, rent rolls, comps)
- Replacing the hand-written parsers with LLM extraction

---

## Ground rules (same as before)

- State what you're about to build and which files before writing code.
- Velocity may still be gated for some or all facilities when this is
  built. A report that honestly says "insufficient history" is a
  successful M7 report. One that shows a made-up or blended number is a
  failure.
- The narrative never introduces a number or claim the table doesn't
  contain. If in doubt, ship the table without the narrative.
- No LLM calls and no BigQuery access from tests or CI. Real-data runs
  against prod marts are deliberate, manual, and confirmed first.
