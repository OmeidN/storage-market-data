# Next Phase Plan — Milestone 3: Docker + CI/CD

Builds on Milestone 2 (Pydantic models, Postgres with append-only
observations, 10 StorQuest facilities, 30 passing tests). Corresponds to
planning.md Phase 21, pulled earlier per the GCP-native restructuring —
this is cheap and low-risk given a working test suite already exists.

**Goal at the end of this phase:** the app runs the same way on any
machine via `docker compose up`, and every push automatically runs the
full test suite in CI. Nothing about the pipeline's behavior changes —
this phase is about reproducibility and safety net, not new features.

---

## Step 1 — Containerize the app

**Build:**
- `Dockerfile` for the app itself (not just Postgres, which is already
  containerized) — install deps from `pyproject.toml`, copy the app,
  set an entrypoint.
- Extend the existing `docker-compose.yml` (currently just Postgres on
  5433) to add an `app` service that depends on `postgres`, shares the
  same network, and reads DB connection info from environment variables
  instead of hardcoded localhost.
- Confirm `alembic upgrade head` and `scripts/scrape_facility.py` both
  run correctly *inside* the container, not just on the host.

**Test:**
- From a clean checkout with nothing installed locally except Docker:
  `docker compose up -d` → run the Alembic migration → run the scraper
  against one facility → confirm data lands in the containerized Postgres.
- This is a manual verification, not a pytest test — the point is
  proving "works on a machine with zero local Python setup," which
  automated tests can't fully confirm on their own.

**Exit criteria:** someone with just Docker installed (no local Python,
no local Postgres) can clone the repo and get a working scrape end to
end using only `docker compose` commands.

---

## Step 2 — CI pipeline (Bitbucket Pipelines)

**Build:**
- `bitbucket-pipelines.yml` that, on every push:
  - spins up a Postgres service container for tests (mirroring the
    existing throwaway `storage_market_data_test` setup),
  - installs the app,
  - runs `alembic upgrade head` against the test database,
  - runs `pytest tests/ -v`.
- Pipeline should fail loudly (non-zero exit) if any test fails —
  no silent partial success.

**Test:**
- Push a commit that deliberately breaks a test (e.g., temporarily flip
  an assertion) and confirm the pipeline actually fails and reports it
  clearly. Then revert and confirm it passes again.
- This is the test for the test infrastructure itself — a CI pipeline
  that always shows green regardless of what's pushed is worse than no
  CI at all, so proving it can fail is as important as proving it can pass.

**Exit criteria:** a genuinely broken commit produces a red pipeline;
the current clean commit produces a green one with all 30 tests passing.

---

## Step 3 — Tidy up for reproducibility

**Build:**
- `.env.example` reflects whatever new container-based env vars exist
  (DB host/port inside Docker vs. host machine).
- README updated with the Docker-based quickstart as the primary path,
  with the manual venv setup kept as a secondary option for local dev.
- Confirm `.gitignore` still correctly excludes `data/raw/*.html`,
  `.env`, and any Docker volumes/state that shouldn't be committed.

**Test:**
- No new tests needed — this step is documentation and hygiene.

**Exit criteria:** a new person (or future you, in six months) can read
the README top to bottom and get a working local environment without
guessing.

---

## Explicitly out of scope for this phase

- Cloud Run / Cloud Scheduler deployment (that's Milestone 4 — this
  phase only gets the app *containerized*, not *deployed*)
- Warehouse/dbt/BI
- Second provider
- Any change to parser, models, or Postgres schema logic — Milestone 3
  should not touch application behavior, only how it's packaged and
  tested

---

## Ground rules (same as before)

- State what you're about to build and which files before writing code.
- Run `pytest tests/ -v` locally after each step, and confirm it also
  passes via the new CI pipeline once Step 2 exists.
- Don't change parser/model/Postgres logic in this phase — if something
  reveals a real bug in that logic while containerizing, flag it
  separately rather than quietly fixing it inline.
