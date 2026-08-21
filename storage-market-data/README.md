# storage-market-data — Milestone 4

StorQuest pricing/availability for a small set of real facilities,
validated with Pydantic and stored as append-only observations in
Postgres. Locally it runs under Docker; in GCP it runs as a Cloud Run
Job on a schedule against Supabase (transaction pooler). GitHub Actions
still uses throwaway Postgres — never the Supabase URL.

## Quickstart (Docker only)

Needs Docker. No local Python or Postgres.

```bash
cd storage-market-data
docker compose up -d
docker compose run --rm app alembic upgrade head
docker compose run --rm app python scripts/scrape_facility.py --limit 1
```

`docker compose up -d` starts Postgres only. The scraper is
`docker compose run --rm app ...` so bringing the stack up does not
hit live StorQuest pages.

Inside Compose, the app talks to Postgres at hostname `db` on port 5432.
That `DATABASE_URL` is set by Compose — do not copy the host `.env`
localhost URL into the container.

To scrape all ~10 facilities:

```bash
docker compose run --rm app python scripts/scrape_facility.py
```

Raw HTML is written to `data/raw/` on the host. Confirm rows landed:

```bash
docker compose exec db psql -U storage -d storage_market_data -c "SELECT count(*) FROM observations;"
```

## Local Python (optional)

Use this if you want a venv on the host talking to the Compose Postgres
published on **5433** (avoids clashing with a native install on 5432).

```bash
cd storage-market-data
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
cp .env.example .env
docker compose up -d
alembic upgrade head
python scripts/scrape_facility.py --limit 1
pytest tests/ -v
```

Parser and model tests run without Postgres. Repository tests need
`DATABASE_URL` (or `TEST_DATABASE_URL`); they use a throwaway
`storage_market_data_test` database, not the dev data. Point pytest at
local Compose Postgres, not Supabase.

## Cloud (GCP + Supabase)

Do not commit `.env` or connection strings. Two URLs:

- `DATABASE_URL` — transaction pooler (`:6543`). Laptop scrape and the Cloud Run Job.
- `DATABASE_URL_DIRECT` — Alembic only. Prefer direct `:5432`. If that host
  does not resolve (Supabase free-tier is often IPv6-only), use the
  **session** pooler (`:5432` on the pooler hostname). Never `:6543`.

```bash
alembic upgrade head
python scripts/scrape_facility.py --limit 1
```

GCP project `storagemarketdata`, region `us-west1` (Oregon, next to
Supabase `us-west-2`). Push the image:

```bash
bash scripts/gcp_push_image.sh
```

The Cloud Run Job `scrape-facilities` uses Secret Manager `DATABASE_URL`
(pooler URI), `RAW_DATA_DIR=/tmp/raw`, and `python scripts/scrape_facility.py`.
The job SA `scrape-job@…` can only read that secret.

Cloud Scheduler `scrape-facilities-schedule` POSTs to the Job daily at
06:00 America/Los_Angeles (`0 6 * * *`). Its SA `scrape-scheduler@…`
has `roles/run.invoker` on that Job only — nothing broader. Manual run:

```bash
gcloud run jobs execute scrape-facilities --region=us-west1 --wait
```

## CI

Every push and pull request runs GitHub Actions: a Postgres 16 service,
`alembic upgrade head`, then `pytest tests/ -v`. The job fails if any
test fails.

## robots.txt check (already done)

```
User-Agent: *
Allow: /
Disallow: /studio/
Sitemap: https://www.storquest.com/sitemap.xml
```

`/self-storage/...` pages are unrestricted. `/studio/` is their CMS admin
panel, unrelated to facility pages. No `Crawl-delay` specified — the
collector still waits `REQUEST_DELAY_SECONDS` (default 3s) between
requests as a courtesy.
