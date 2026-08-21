# Next Phase Plan — Milestone 4: Cloud Run + Cloud Scheduler

Builds on Milestone 3 (containerized app, GitHub Actions CI, 30 passing
tests). Corresponds to planning.md's old "Phase 22 — Cloud Pilot," made
concrete and GCP-native. This phase deploys what already exists — same
10 facilities, same parser, same schema. No new features.

**Before starting:** decide the Postgres hosting question above (Neon/
Supabase free tier vs. Cloud SQL) — this changes Step 2 below.

**Goal at the end of this phase:** the same scrape that currently runs
via `docker compose run --rm app ...` on your machine instead runs
automatically, on a schedule, in the cloud, with no laptop involved.

---

## Step 1 — GCP project + Artifact Registry

**Build:**
- A GCP project (or reuse one you already have) with billing enabled —
  flag to yourself that this phase has a real cost, unlike Docker/GitHub
  Actions. Set a billing budget alert (e.g. $5) as a safety net.
- Enable the Cloud Run, Cloud Scheduler, and Artifact Registry APIs.
- Push the existing app image (already built in Milestone 3) to Artifact
  Registry instead of only building it locally.

**Test:**
- Confirm the image is visible in the Artifact Registry console/CLI
  after push. No pytest test needed — this is infrastructure setup.

**Exit criteria:** `gcloud artifacts docker images list` shows the pushed
image.

---

## Step 2 — Database reachable from GCP

**Build:**
- If Neon/Supabase: create a free-tier Postgres instance, run the
  existing Alembic migrations against it once, confirm connectivity from
  your local machine first.
- If Cloud SQL: provision the smallest instance, enable the Cloud SQL
  Auth Proxy / Unix socket connection Cloud Run expects, run migrations
  against it.
- Store the resulting connection string in Secret Manager — not as a
  plaintext env var in the Cloud Run config, and not committed anywhere.

**Test:**
- From your local machine, point `DATABASE_URL` at the new cloud DB and
  run `python scripts/scrape_facility.py --limit 1` — confirm it writes
  to the cloud database, not local Postgres.
- Existing pytest suite continues to run against the local/throwaway
  test DB as before — this step doesn't change what CI tests against.

**Exit criteria:** a manual scrape from your laptop writes a real
observation row into the cloud-hosted database.

---

## Step 3 — Cloud Run Job (not Service)

**Build:**
- Deploy as a **Cloud Run Job**, not a Cloud Run Service. This matters:
  a Service expects to handle HTTP requests and stay warm; a Job runs to
  completion and stops, which is what a scrape actually is. Using
  Service here would be the wrong tool and would cost more for no reason.
- Configure the Job to pull `DATABASE_URL` from Secret Manager at
  runtime, using the image pushed in Step 1.
- Keep the existing `--limit` / facility-list behavior as-is — no change
  to what the script does, only how/where it runs.

**Test:**
- Manually trigger the Job once (`gcloud run jobs execute`) and confirm:
  - it completes successfully,
  - new observation rows appear in the cloud database,
  - logs are visible in Cloud Logging, including for the 10-facility
    per-facility error handling from Milestone 2 (a forced bad URL
    should still log and not crash the whole job, same as it does locally).

**Exit criteria:** one manual Cloud Run Job execution completes and
produces the same result as running `scrape_facility.py` locally against
the cloud DB.

---

## Step 4 — Cloud Scheduler

**Build:**
- A Cloud Scheduler job that invokes the Cloud Run Job on a schedule
  (start with something easy to observe, e.g. every few hours, before
  settling on a real daily cadence).
- Correct IAM: Scheduler needs permission to invoke the Job; the Job's
  service account needs permission to reach Secret Manager and the
  database — nothing broader than that.

**Test:**
- Let the scheduled trigger fire at least twice unattended and confirm
  in Cloud Logging / the database that both runs happened without you
  manually invoking anything.
- Deliberately misconfigure IAM once (e.g. wrong service account) in a
  throwaway test to confirm the failure is visible/loud in Cloud
  Logging, not silent — same "prove it can fail" principle as the CI
  pipeline in Milestone 3.

**Exit criteria:** two consecutive unattended scheduled runs both
produce new observation rows, with no manual trigger involved.

---

## Explicitly out of scope for this phase

- Warehouse/dbt/BI layer (Milestone 5)
- Second provider
- Scaling past the current 10 facilities
- Any change to parser, models, or schema
- Cloud Composer/Airflow — not needed yet; Scheduler + Run is enough
  until there's real multi-provider dependency logic to orchestrate

---

## Ground rules (same as before)

- State what you're about to build and which files/GCP resources before
  acting — cloud resources cost money and are easy to leave running by
  accident, more so than local Docker.
- After Step 4, actually check the GCP billing page once to confirm
  costs look like what was expected, not a surprise.
- Don't touch parser/model/DB logic in this phase.
