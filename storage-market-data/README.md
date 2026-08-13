# storage-market-data — day one

Milestone 1 skeleton: one provider (StorQuest), one facility (Tracy, CA),
no database yet. Corresponds to Phases 1–6 of `planning.md`.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
cp .env.example .env
```

## Run it

```bash
python scripts/scrape_facility.py
```

This fetches the real Tracy, CA StorQuest page, saves the raw HTML to
`data/raw/`, parses it, and prints the result as JSON.

## Run tests

```bash
pytest tests/ -v
```

## What's real vs. what's a placeholder right now

- **Real and working:** the HTTP collector, raw-response saving, project
  structure, test setup.
- **Not yet verified:** `app/providers/storquest/parser.py`. It was written
  from a text preview of the live page, not the real HTML/DOM — see the
  warning comment at the top of that file. The synthetic test fixture in
  `tests/fixtures/` was hand-built to match that same text preview, so the
  tests currently passing only prove the parsing *logic* works, not that
  it's correct against the real site.

**First real task:** run `scripts/scrape_facility.py`, inspect the saved
HTML in `data/raw/`, and fix the parser (and swap in a real fixture) to
match what's actually there. `CURSOR_PROMPT.md` has the full brief for
this.

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
