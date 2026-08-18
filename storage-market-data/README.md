# storage-market-data — Milestone 2

StorQuest pricing/availability for a small set of real facilities,
validated with Pydantic and stored as append-only observations in
Postgres. Corresponds to `MILESTONE_2_PLAN.md`.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
cp .env.example .env
docker compose up -d
alembic upgrade head
```

## Run it

```bash
python scripts/scrape_facility.py
```

Fetches ~10 StorQuest facility pages (Tracy, CA first), saves raw HTML to
`data/raw/`, validates each parse, writes append-only observations to
Postgres, and prints JSON. One facility failing does not stop the rest.

## Run tests

```bash
pytest tests/ -v
```

Parser and model tests run without Postgres. Repository tests need a
running database (`DATABASE_URL` in `.env`, or `TEST_DATABASE_URL`); they
use a throwaway `storage_market_data_test` database, not the dev data.
Docker Compose publishes Postgres on host port **5433** so it does not
clash with a native install on 5432.

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
