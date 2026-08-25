# Milestone 4 — Unattended scrape in GCP

**Status:** closed  
**Commit:** `c9efcf6`  
**CI:** [actions/runs/32515841804](https://github.com/OmeidN/storage-market-data/actions/runs/32515841804) — **success**

---

## What was created, and why

Until M4, history only accumulated when someone ran the scraper. Velocity needs **daily snapshots without a laptop**. This milestone deployed the existing 10-facility scrape as a Cloud Run **Job** (run-to-completion, not a standing HTTP service) on a schedule, against hosted Postgres.

**What shipped:**

- GCP project `storagemarketdata`, region `us-west1` (next to Supabase `us-west-2`). Artifact Registry image for the M3 Dockerfile.
- **Supabase** as Postgres: `DATABASE_URL` = transaction pooler `:6543` (app + Job); `DATABASE_URL_DIRECT` = Alembic only (session pooler `:5432` after direct `:5432` failed DNS/IPv6). Engine: `pool_pre_ping`; pooler connections set `prepare_threshold=None`.
- Secret Manager `DATABASE_URL`. Job SA `scrape-job@` can read that secret and nothing broader.
- Cloud Run Job `scrape-facilities` — `python scripts/scrape_facility.py`, `RAW_DATA_DIR=/tmp/raw`.
- Cloud Scheduler `scrape-facilities-schedule` — `0 6 * * *` America/Los_Angeles. Scheduler SA `scrape-scheduler@` has `roles/run.invoker` on **that job only**.
- Project-scoped billing budget **`storagemarketdata $5 monthly`** (50% / 90% / 100%).

Parser, Pydantic models, and schema were not changed. Same 10 facilities as M2.

## What was tested, and the results

| Check | Result |
|---|---|
| Laptop scrape → Supabase | Wrote real observation rows into the cloud DB, not local Compose |
| Manual `gcloud run jobs execute scrape-facilities` | Completed; **126 new observations** (11 → 137) across all 10 facilities; logs in Cloud Logging |
| IAM deny (throwaway SA, no invoker) | Loud failure in logs — not a silent miss |
| Two unattended Scheduler fires (temporary `*/5` cadence, then daily) | Both succeeded, **RUN BY** `scrape-scheduler@…`: executions `kjwbv` (~18:35 UTC) and `b6r2z` (~18:40 UTC) |
| CI on `c9efcf6` | Green — [run 32515841804](https://github.com/OmeidN/storage-market-data/actions/runs/32515841804) |
| Cost sanity | Cloud Run Job used ~180 billable instance-seconds across the early runs (cents-scale). Invoice UI needs a logged-in console check. |

Later close-out used the same bar as the plan: **Scheduler-triggered successes**, not only local or manual executes. Daily 06:00 PT is the production cadence.

## How this contributes to the bigger picture

Observation history is now a **time series**, not a demo. Each morning’s scrape is another point on the curve that M5 turns into days-to-lease.

This is also the production pattern later jobs copy: least-privilege SAs, secrets out of git, Job not Service, Scheduler with a timezone. M5’s `replicate-to-bigquery` job at 06:30 PT is a sibling of this scrape, not a rewrite of it.

The north star still does not need a client dashboard here. M4’s job is boring on purpose: keep asking StorQuest the same question every day so the warehouse can eventually say, honestly, how fast units rent.
