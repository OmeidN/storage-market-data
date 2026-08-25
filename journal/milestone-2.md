# Milestone 2 — Validated history in Postgres, ten facilities

**Status:** closed  
**Commit:** `b94ef1b`

---

## What was created, and why

Milestone 1 could print a correct snapshot. Milestone 2 made that snapshot **durable, validated, and repeatable** — the minimum needed for any later “how fast did this rent?” question.

Three pieces, in order:

1. **Pydantic models** (`Facility`, `Unit`, `Observation`, `FacilityPage`). Parser dicts must round-trip through validation. Missing prices, bad sizes, and empty parses raise clearly instead of becoming fake inventory. `NO_UNITS` / `FAILED` is distinct from “every unit is sold out.”
2. **Postgres as system of record.** Docker Compose Postgres on host port **5433**, SQLAlchemy tables `facilities` / `units` / `observations`, Alembic `001_initial_schema`. `save_observation()` upserts facility and unit identity, then **always appends** a new observation row. History is never overwritten.
3. **Ten real StorQuest facilities**, hand-picked (not discovered). A runner loops the same collect → parse → validate → store path, with the existing request delay, and continues if one facility fails.

That last point is why this milestone exists: one Tracy snapshot cannot support market comparison. Ten facilities, re-scraped over days, is the start of observation history.

## What was tested, and the results

Local suite: **`pytest tests/ -v` → 30 passed, 0 failed.**

| Area | What it checked | Result |
|---|---|---|
| Tracy parser fixture (8 tests) | Name, address, 12 units, Next.js JSON strategy, specific size/price/availability cases | Matched the saved snapshot |
| Pydantic models | Valid parse → models; malformed input → `ValidationError`; empty parse ≠ sold out | Passed |
| Repository / Alembic | Fresh migrate creates the three tables; two saves of the same facility grow observations only; facilities/units are not duplicated; `FAILED` writes no sold-out rows | Passed (throwaway `storage_market_data_test`, not dev data) |
| Per-facility fixtures | Real saved HTML for each of the 10 URLs parses `OK` via `next_data_json`; Anaheim / Arlington / Apopka spot checks | Passed |
| Live run | All 10 facilities collected in one run | **10/10 succeeded** → **10 facilities, 132 units, 132 observations** |
| Live spot-check | Anaheim, Arlington, Apopka vs the live site (sizes, standard vs promo, availability) | Matched |

A broken/missing URL in the list logs and continues; it does not abort the other nine.

## How this contributes to the bigger picture

Rental velocity is “unit present on snapshot T, gone (or sold out) on snapshot T+1,” measured across real time. That metric **cannot exist** without append-only observations and a rule that a failed scrape is not a lease.

Milestone 2 is the system of record later phases only read:

- M4’s Cloud Run Job writes the same tables, on a schedule, in Supabase.
- M5 replicates those tables into BigQuery and computes days-to-lease from them.
- M7’s client report will compare properties using this history, not a one-off scrape.

It also proved the parser’s JSON shape held across ten different cities, so scaling the *collection* list is an operations problem, not a rewrite of the extractor.
