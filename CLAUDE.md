# CLAUDE.md

Self-storage (and now warehouse/industrial) market-intelligence pipeline:
scrape public listings → validate → append-only Postgres history →
BigQuery/dbt marts → rental velocity (avg days-to-lease). Product goal and
scope boundary: `storage-market-data/NORTH_STAR.md`. Milestone roadmap:
`storage-market-data/ROADMAP_M5_PLUS.md`.

Layout: the Python project lives in `storage-market-data/` (app, alembic,
scripts, tests, warehouse/dbt, docs, milestone plans). The repo root holds
only `.github/workflows/ci.yml`, `journal/`, and this file.

## Milestone workflow

- **Before building:** a `storage-market-data/MILESTONE_N_PLAN.md`, in the
  same style as the existing ones: goal paragraph, numbered steps each with
  **Build / Test / Exit criteria**, "Explicitly out of scope", "Ground rules".
  Get it agreed before writing code.
- **After building:** a `journal/milestone-N.md`, same format as the existing
  journals: title, `**Status:**`, `**Commit:**`, `**CI:**` link when there is
  one, then three sections — *What was created, and why* / *What was tested,
  and the results* (tables, real numbers) / *How this contributes to the
  bigger picture*.
- **Scope:** never build, stub, or scaffold anything beyond the current
  milestone. No empty modules "for later", no placeholder interfaces for the
  next milestone. If something belongs to a later milestone, name it in the
  plan's out-of-scope list and stop.
- State what you're about to build and which files before writing code.
  Avoid unrelated refactors.

## Invariants (do not break; tests guard them)

- **History is append-only.** `save_observation()` upserts facility/unit
  identity and always appends observations. Never update or delete
  observation rows. Schema changes go through Alembic migrations that
  backfill without data loss.
- **A failed or empty scrape is never "sold out".** `FAILED` / `NO_UNITS`
  persist nothing. Absence from a listing is not unavailability.
- **A scrape gap is never a lease.** Lease inference compares consecutive
  *actual* OK snapshots per facility (`LAG` on timestamps), never calendar
  days. Confirmed and inferred tiers are never blended.
- **Velocity stays gated.** `insufficient_history` unless ≥14 snapshot dates
  and ≥2 events in that tier; when gated, `avg_days_to_lease` is NULL.
- Load-bearing definitions live in `storage-market-data/docs/velocity_definitions.md`;
  cite it, don't re-derive rules in SQL comments.
- ReadySpaces publishes no prices: `price` is null and
  `price_data_available = false`. That is expected, not a bug.

## Parsers vs LLM

The hand-written parsers (`app/providers/*/parser.py`) are the production
path. The Gemini extractor (`scripts/compare_llm_parser.py`) is a prototype
for comparison only. Do not wire it into `scrape_facility.py` or the Cloud
Run job.

## Environments and secrets

- CI and tests use throwaway Postgres (Compose / GitHub service) or DuckDB
  (dbt `ci` target). **Never Supabase**, never BigQuery from tests.
- **Watch out:** the local `storage-market-data/.env` points `DATABASE_URL`
  and `DATABASE_URL_DIRECT` at Supabase. `app/config.py` calls
  `load_dotenv()`, which does not override variables already set. So for any
  host-side alembic/pytest run, export the local URLs first (see Commands).
- Never commit `.env`, API keys (`GEMINI_API_KEY`), service-account keys, or
  connection strings. `.env.example` uses placeholders only.
- Do not run anything against Supabase, GCP (Cloud Run, Scheduler, Secret
  Manager), or BigQuery (`--target prod`, `replicate_to_bigquery.py`) without
  asking first.

## Collection etiquette

- Check `robots.txt` (and ToS for automated access) before onboarding any
  provider. Keep `REQUEST_DELAY_SECONDS` (default 3s) between requests.
- No CAPTCHA bypass, stealth, or proxy rotation. Detect, back off, record.
- Develop parsers against saved fixtures in `tests/fixtures/`, not live
  pages. Ask before any live scrape or other network call to a provider site.

## Commands

Run from `storage-market-data/`. Use the venv (`.venv/Scripts/python.exe` on
Windows) or Docker.

```bash
docker compose up -d                       # Postgres only, host port 5433

# Point host tools at local Compose, not the Supabase URLs in .env
export DATABASE_URL=postgresql+psycopg://storage:storage@localhost:5433/storage_market_data
export DATABASE_URL_DIRECT=$DATABASE_URL
export TEST_DATABASE_URL=postgresql+psycopg://storage:storage@localhost:5433/storage_market_data_test

alembic upgrade head
pytest tests/ -v                           # repo tests use storage_market_data_test

# Same thing fully inside Docker (Compose sets DATABASE_URL to db:5432)
docker compose run --rm app alembic upgrade head
```

dbt on DuckDB (same as the CI `dbt` job; no secrets):

```bash
cd warehouse
dbt seed --target ci --profiles-dir .
dbt run  --target ci --profiles-dir .
dbt test --target ci --profiles-dir .
```

CI (`.github/workflows/ci.yml`) runs two jobs on every push/PR: `test`
(Postgres 16 service → alembic → pytest) and `dbt` (DuckDB seed → run → test).
