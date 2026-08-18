# Next Phase Plan — Milestone 2

Builds on the Milestone 1 skeleton (one provider, one facility, no
database). Corresponds to planning.md Phases 3, 7, and the start of
Phase 4 (scaling within one provider). Do not start Phase 20+ (queue),
Playwright, Docker, second provider, or dashboard work — those come
after this milestone, not alongside it.

**Goal at the end of this phase:** StorQuest data for ~10 real facilities,
validated and stored in Postgres with correct history semantics, with
tests proving both the happy path and the failure modes.

---

## Step 1 — Data models (planning.md Phase 3)

**Build:**
- Pydantic models for `Facility`, `Unit`, `Observation` (a single
  price/availability snapshot at a point in time — this is the append-only
  history record, not something that gets overwritten).
- Move the parser's plain-dict output through these models. Validation
  errors (missing price, malformed size, etc.) should raise clearly, not
  fail silently.
- Explicitly model "unknown/unavailable" separately from "sold out" —
  this is the exact invariant your own planning.md calls out (§88): a
  failed scrape must never be recorded as if the unit were confirmed sold
  out.

**Test:**
- Valid parser output round-trips into models correctly.
- Malformed/partial input raises a validation error rather than
  silently producing wrong data.
- A "parser found nothing" case is distinguishable in the model from
  "parser found units and all are sold out."

**Exit criteria:** `scrape_facility.py` prints validated Pydantic objects
instead of a raw dict, and a bad fixture triggers a clear validation
failure in a test.

---

## Step 2 — Postgres (planning.md Phase 7)

**Build:**
- Local Postgres (Docker Compose is fine for local dev only — this is
  not the same as "Phase 21 Docker," it's just the easiest way to run
  Postgres locally right now).
- SQLAlchemy models mirroring `facilities`, `units`, `observations`.
- Alembic migration for the initial schema.
- A `save_observation()` function that:
  - inserts a new facility/unit row if it doesn't exist,
  - always **appends** a new observation row — never updates/overwrites
    a previous observation, per your history-integrity rule.
- Update `scrape_facility.py` to write to Postgres instead of (or in
  addition to) printing JSON.

**Test:**
- Running the pipeline twice against the same facility produces two
  observation rows, not one overwritten row.
- A facility/unit that already exists doesn't get duplicated on a second
  run — only the observation table grows.
- A failed scrape does not write a "sold out" observation (ties back to
  Step 1's failure-vs-sold-out distinction).
- Use a throwaway test database or transaction rollback per test — don't
  let tests write into your real dev data.

**Exit criteria:** running `scrape_facility.py` against the Tracy page
twice produces two distinct timestamped observation rows in Postgres,
verifiable with a plain SQL query.

---

## Step 3 — Scale to ~10 StorQuest facilities (planning.md Phase 4)

**Build:**
- A small, explicit list of ~10 real StorQuest facility URLs (hand-picked
  for now — sitemap-based discovery is a later phase, don't build it yet).
- A runner that loops over that list, calling the same collect → parse →
  validate → store pipeline per facility, with the existing per-request
  delay respected between each.
- Per-facility error handling: one facility failing (network error, parser
  mismatch, unexpected page structure) should not crash the whole run or
  silently drop that facility — log it and continue.

**Test:**
- Run against all 10 real facilities and manually spot-check at least 2–3
  against the live pages for correctness (sizes, prices, availability).
- Save each facility's raw HTML as a fixture and add a parser test per
  fixture — this is where the parser's "unverified" edge cases will
  surface: different unit mixes, no promo pricing, no availability text,
  a fully sold-out facility, a facility with only one unit type, etc.
- A deliberately broken/missing facility URL in the list doesn't halt the
  other 9.

**Exit criteria:** all 10 facilities collected, parsed, and stored in one
run; a test fixture and passing test exist for each; the run's log output
clearly shows any per-facility failures without crashing.

---

## Explicitly out of scope for this phase

Don't start these even if they seem like natural next steps — they come
after Milestone 2 is solid, per planning.md's phase ordering:

- Job queue / scheduler (Redis, Celery, Cloud Composer)
- Playwright / browser fallback
- A second provider
- Docker for anything beyond local Postgres
- Warehouse/dbt/BI layer
- Sitemap-based facility discovery

If something here feels like it's forcing a workaround (e.g., "I really
need retries to get through all 10 facilities cleanly"), flag it and ask
rather than quietly building the resilience layer early.

---

## Ground rules (same as before)

- State what you're about to build and which files before writing code.
- Run `pytest tests/ -v` after each step and report the result.
- Don't touch files outside what a step requires.
- If real data reveals the parser's Next.js JSON assumptions were wrong
  in a new way, fix it and note what changed — this is expected, not a
  failure.
