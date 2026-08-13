# Prompt for Cursor

Paste everything below this line into Cursor as your instruction.

---

## The full project, for context only

`planning.md` in this repo is the long-term vision: a scalable,
multi-provider data pipeline that discovers self-storage facilities,
collects pricing and availability on a schedule, parses and normalizes
it, validates it, keeps full history in PostgreSQL, and eventually
supports analytics and a dashboard — scaling from one facility to
nationwide coverage over many months.

**Read `planning.md` for context on where this is headed. Do not implement
it.** It's a long-term reference, not a sprint backlog. Almost everything
in it — the provider registry, job queue, scheduler, Playwright,
PostgreSQL, resilience/circuit-breakers, Docker, multiple providers,
geographic scaling — is explicitly out of scope right now. Don't build,
stub, or scaffold any of it "for later" unless I ask for it by name.

## What already exists in this repo

A deliberately small day-one skeleton, already working end-to-end at a
basic level:

- `app/config.py` — plain settings, no provider registry
- `app/logging.py` — basic logging
- `app/collectors/http.py` — fetches one URL, returns the raw response.
  No parsing, no retries, no fallback to a browser.
- `app/raw_storage.py` — saves raw HTML to `data/raw/`
- `app/providers/storquest/parser.py` — turns raw HTML into a plain dict
  of units. **Unverified against real StorQuest markup** — read the
  warning comment at the top of that file before trusting anything in it.
- `scripts/scrape_facility.py` — runs collector → save → parse → print,
  targeting one real facility:
  `https://www.storquest.com/self-storage/ca/tracy/225-gandy-dancer-drive`
- `tests/test_storquest_parser.py` — passes against a **synthetic**
  fixture built from a text preview of the live page, not real saved HTML

This corresponds to Phases 1–6 in `planning.md` ("Phase 1 — Foundation"
through "Phase 6 — Parser"), stopped short of Phase 7 (PostgreSQL).

**robots.txt has already been checked** for storquest.com:
```
User-Agent: *
Allow: /
Disallow: /studio/
Sitemap: https://www.storquest.com/sitemap.xml
```
`/self-storage/...` pages are unrestricted, so collecting from this URL is
fine. Keep the request delay in `app/config.py` in place regardless.

## What I want you to do right now

1. Run `scripts/scrape_facility.py` and confirm it fetches the real page
   and saves raw HTML to `data/raw/`.
2. Open that saved raw HTML file and inspect the real structure around
   unit sizes, prices, and availability text. In particular, check
   whether a `<script id="__NEXT_DATA__" type="application/json">` tag
   exists and contains the unit/pricing data — if it does, that's a much
   more reliable extraction path than scraping visible text, and
   `_parse_next_data()` in the parser should be finished using the real
   field names instead of the placeholder guesses currently there.
3. If `__NEXT_DATA__` doesn't pan out, fix `_parse_visible_text()` in
   `app/providers/storquest/parser.py` against the real saved HTML until
   its output correctly matches the live page for all ~12 units (size,
   standard price, promotional price, climate-controlled flag,
   drive-up/ground-level/vehicle-parking flags, availability text).
4. Replace `tests/fixtures/storquest_tracy_sample.html` with a real saved
   response (trim it if you want, but keep it real, not synthetic) and
   update `tests/test_storquest_parser.py` to match the corrected output.
5. Stop there. Do not add a database, a second facility, a second
   provider, Pydantic models, or anything from later phases unless I
   explicitly ask.

## Ground rules while working on this

- Before writing code for a step, briefly tell me what you're about to do
  and which files you'll touch.
- Don't refactor files I haven't asked you to touch.
- After making changes, run `pytest tests/ -v` and show me the result.
- If something in `planning.md` seems relevant to solving the current
  step, it's fine to be informed by it — but flag it explicitly (e.g.
  "this matches planning.md's normalized-pricing pattern") rather than
  silently pulling in scope from later phases.
- If you think we should skip ahead to a later phase (e.g. "this really
  needs a database"), say so and ask — don't just build it.
