# Milestone 6 — Second vertical and a generalized listing model

**Status:** closed (Gemini comparison numbers pending; see below)  
**Commit:** `e3ed361`  
**CI:** _TODO: add the GitHub Actions run URL for `e3ed361` (test + dbt)_

---

## What was created, and why

Through M5 the schema was self-storage-shaped: `width_ft` × `length_ft`, a monthly per-unit price, and nothing else. The product is meant to compare properties across verticals (`NORTH_STAR.md`), so M6 forced the model to generalize by onboarding a second vertical — warehouse/industrial — instead of a second storage site. A second storage provider would have fit the old columns and proved nothing.

**Provider: ReadySpaces** (`readyspaces.com`), small-format flex warehouse space in size tiers. `robots.txt` is fully open with a sitemap; terms have no anti-automation clause (WareSpace was ruled out because it requires written permission). The decision that shaped everything else: **ReadySpaces does not publish per-listing prices** ("Contact for Pricing"). It was onboarded for square footage, availability, and attributes only.

**What shipped:**

- **Alembic `002_listing`** — adds Listing-shaped columns without renaming tables:
  - `facilities.asset_type` (`self_storage` default) and `facilities.attributes` (JSONB).
  - `units.square_footage` (backfilled as `width_ft * length_ft`, then `NOT NULL`), `units.attributes` (backfilled with width/length/features), `units.price_data_available`. `width_ft` / `length_ft` become nullable.
  - `observations.price`, `price_unit`, `price_data_available`, backfilled from `standard_price` as `per_unit_per_month`.
  - Additive only. Every pre-M6 StorQuest observation stays queryable; no history rewritten.
- **One Pydantic model, two verticals.** `app/models.py` validates a storage unit and a warehouse space through the same `Listing` path — different `price_unit` and `attributes`, not a parallel model. `price_data_available = false` is distinct from an unknown price: a null price is only valid when the provider is known not to publish one.
- **ReadySpaces collector + parser** (`app/providers/readyspaces/`). Plain HTTP first; inventory is server-rendered in the unit slider (unit id, sqft, availability, size tier), plus facility attributes like clear height, dock-high doors, drive-in bays. Cloudflare block pages are detected and trigger a Playwright fallback (`app/collectors/playwright.py`, optional `[browser]` extra) — never parsed as inventory.
- **Three hand-picked facilities**: Downtown LA, Redmond, South Gate. `scripts/scrape_facility.py --provider {all,storquest,readyspaces}`; default is both.
- **dbt on universal fields.** Staging carries `asset_type`, `square_footage`, `price`, `price_unit`, `price_data_available`. `price_history_by_market` filters to `price_data_available`, so ReadySpaces is absent rather than silent $0 rows. Market seed extended with the three facilities. `velocity_definitions.md` gained rules 5–6: ReadySpaces velocity is **inferred-only** (its pages only list available units, so `SOLD_OUT` never fires).
- **LLM extraction prototype** (`scripts/compare_llm_parser.py`, `docs/llm_extraction_readyspaces.md`): Gemini Flash-Lite on cleaned page text, compared against the parser on the same fixtures. Not wired into the scrape.

## What was tested, and the results

Local re-run on 2026-10-25 against Compose Postgres and DuckDB: **`pytest tests/ -v` → 45 passed, 0 failed**; **dbt ci → 5 seeds, 9 models, 7 tests, all pass.**

| Area | What it checked | Result |
|---|---|---|
| Migration backfill (`test_alembic_backfills_existing_storquest_rows`) | Pre-M6 StorQuest rows survive `002_listing` with `square_footage`, `attributes`, and `price` filled correctly | Pass |
| Warehouse persistence (`test_warehouse_listing_persists_without_width_or_price`) | A listing with no width/length and no price saves cleanly | Pass |
| Same-model validation (`test_models.py`) | Warehouse listing round-trips through the storage model; no-price listing valid only with `price_data_available = false`; price still required when the flag is true | Pass |
| M2–M5 invariants | Append-only saves, failed scrape ≠ sold out, empty parse ≠ sold out, broken facility doesn't halt others | Pass (unchanged) |
| ReadySpaces fixtures | Downtown LA **7** units, Redmond **2**, South Gate **19**; K8 = 1,900 sq ft; Redmond D3 850 / E4 1,000 with no price; South Gate G3 = 3,000 enterprise | Pass |
| Live spot-check | Downtown LA K8 vs live page: 1,900 sq ft, "Contact for Pricing" | Matched (recorded in `docs/llm_extraction_readyspaces.md`) |
| M5 dbt regression | `assert_gap_is_not_a_lease`, both lease tiers emitted and distinct, gated → NULL, ungated confirmed → number | Pass |
| New dbt test | `assert_unpublished_price_absent_from_history` — a `price_data_available = false` facility has zero price-history rows | Pass |
| LLM vs parser | Accuracy, latency, tokens, cost per page | **Pending** — no `GEMINI_API_KEY` at close-out; table in the doc is parser-only |

**Not confirmed from the repo — check before relying on it:**

- _TODO:_ The Downtown LA (22 lines) and Redmond (40 lines) fixtures are compact extracts, not full saved pages. Confirm they were trimmed from real responses, per the "no synthetic fixtures once real ones exist" rule.
- _TODO:_ Whether the scrape image in Artifact Registry was rebuilt after `e3ed361`. If it was, the 06:00 job now scrapes ReadySpaces too (default `--provider all`). The Dockerfile installs without `[browser]`, so a Cloudflare block in Cloud Run fails that facility instead of falling back to Playwright — acceptable (fail ≠ sold out), but worth knowing.

**Decision on LLM extraction:** keep the hand-written parser as production. The prototype stays a comparison; the numbers will be added to `docs/llm_extraction_readyspaces.md` when the script is run with a key. No automatic cutover.

## How this contributes to the bigger picture

M6 is the step that makes "compare any two properties" a schema fact rather than a hope. The core marts now read `square_footage`, `price`, `price_unit`, and `price_data_available`; storage-specific detail lives in `attributes`. A third vertical should be a provider adapter and some attributes, not another migration of the core.

It also kept the honesty rules intact under pressure. A provider with no prices could easily have produced $0 price history or a velocity number built on a tier that can never fire. Instead, missing price is modelled explicitly, ReadySpaces velocity is labelled inferred-only, and every M5 gate still holds after the migration.

What this milestone deliberately is not:

- **M7** — the first client-facing artifact: a static comparison report (table + LLM narrative, asking-side scope only) for 2+ properties in one vertical.
- **M8** — interactive dashboard, after the static report is proven.

Velocity is still gated for every facility; ReadySpaces history only started with this milestone. The first report will have to say so plainly.
