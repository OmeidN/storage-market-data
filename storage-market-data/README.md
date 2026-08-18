# storage-market-data — Milestone 3

StorQuest pricing/availability for a small set of real facilities,
validated with Pydantic and stored as append-only observations in
Postgres. The app runs the same way on any machine with Docker;
GitHub Actions runs the full test suite on every push.

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
`storage_market_data_test` database, not the dev data.

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
