# Milestone 3 — Docker + CI

**Status:** closed  
**Commit:** `27f4625` (packaging). Fail-proof: `8552216` (red) then `eb0d1ad` (green revert).

---

## What was created, and why

Milestone 2 worked on one laptop with a local venv. That is not a pipeline. Milestone 3 made the **same scrape** runnable on a clean machine and **automatically tested on every push**, without changing parser, models, or schema behavior.

**What shipped:**

- `Dockerfile` — install from `pyproject.toml`, app at `/app`.
- Compose `app` service next to existing Postgres. `docker compose up -d` starts **Postgres only** so bringing the stack up does not hit live StorQuest. Scrapes are `docker compose run --rm app ...`.
- GitHub Actions (substituted for the plan’s Bitbucket file because origin is GitHub): Postgres 16 service, `alembic upgrade head`, `pytest tests/ -v`. Non-zero exit on any failure. CI uses throwaway Postgres — never a production URL.
- README Docker-first quickstart; `.env.example` documents host vs container `DATABASE_URL`.

One packaging fix: a relative `RAW_DATA_DIR=data/raw` resolved under `site-packages` after `pip install`. Compose/Dockerfile use `/app/data/raw` so the host volume mount works. No collection logic change.

## What was tested, and the results

**Local pytest** stayed **30 passed** — this milestone was not supposed to change app behavior.

**Docker end-to-end (manual, as planned):** from Compose, Alembic already at head; `python scripts/scrape_facility.py --limit 1` scraped Tracy inside the container. Observations **132 → 143** (Tracy gained a second snapshot). The container used Compose’s `db:5432` URL, not the host `.env` localhost URL.

**CI must be able to fail** — a pipeline that is always green is worse than none:

| Run | What | Result |
|---|---|---|
| [32197619169](https://github.com/OmeidN/storage-market-data/actions/runs/32197619169) | Docker/CI commit `27f4625` | **success** |
| [32197810200](https://github.com/OmeidN/storage-market-data/actions/runs/32197810200) | Assertion flipped to `len(units) == 9999` | **failure** (loud) |
| [32197911214](https://github.com/OmeidN/storage-market-data/actions/runs/32197911214) | Revert | **success** |

## How this contributes to the bigger picture

Cloud Run (M4) deploys **this image**. If the container cannot migrate and scrape locally, it will not scrape in GCP either.

CI is the safety net for every later change: M4’s pooler/engine work, M5’s dbt job, and anything in M6+ that must not silently break the parser or append-only store. The red-then-green proof means a broken velocity test or a broken parser assertion will actually stop a merge, instead of looking like a passing pipeline.
