# Instructions for Cursor

## The full project, for context only

`planning.md` in this repo describes the long-term vision: a scalable,
multi-provider data pipeline that discovers self-storage facilities,
collects pricing/availability on a schedule, parses and normalizes it,
validates it, stores full history in PostgreSQL, and eventually supports
analytics and a dashboard — scaling from one facility to nationwide
coverage over many months.

**Read `planning.md` for context on where this is headed. Do not implement
it.** It is a long-term reference document, not a sprint backlog. Almost
everything in it — the provider registry, the job queue, the scheduler,
Playwright, PostgreSQL, resilience/circuit-breakers, Docker, multiple
providers, geographic scaling — is explicitly out of scope right now and
should not be built, stubbed, or scaffolded "for later" unless I ask for
it by name.

## What actually exists right now, and why

This repo currently contains a deliberately small day-one skeleton:

- `app/config.py` — settings
- `app/logging.py` — basic logging
- `app/collectors/http.py` — fetches one URL, returns the raw response. No parsing, no retries.
- `app/raw_storage.py` — saves the raw HTML to `data/raw/` so we can develop the parser offline
- `app/providers/storquest/parser.py` — turns raw HTML into a plain dict of units. **Unverified against real StorQuest markup** — see the warning comment at the top of that file.
- `scripts/scrape_facility.py` — runs collector → save → parse → print for one facility
- `tests/test_storquest_parser.py` — passes against a hand-built fixture, not real data yet

This corresponds to Phases 1–6 in `planning.md`'s roadmap (§ "Phase 1 —
Foundation" through "Phase 6 — Parser"), stopped short of Phase 7
(PostgreSQL). One provider (StorQuest), one facility (Tracy, CA), no
database yet.

## What I actually want you to do right now

The current task is to get this skeleton working against the **real**
StorQuest page and make sure the extracted data is actually correct:

1. Run `scripts/scrape_facility.py` and confirm it successfully fetches
   `https://www.storquest.com/self-storage/ca/tracy/225-gandy-dancer-drive`
   and saves a raw HTML file to `data/raw/`.
2. Open that saved raw HTML file and inspect the real structure around
   unit sizes, prices, and availability text. Confirm (or correct) the
   assumptions in `app/providers/storquest/parser.py` — the regex-based
   approach there was written from an extracted text preview, not the
   real DOM, and is explicitly flagged as unverified.
3. Fix the parser against the real saved HTML until its output correctly
   matches what's actually shown on the live page for all ~12 units
   (sizes, standard price, promotional price, climate-controlled flag,
   drive-up/ground-level/vehicle-parking flags, availability text).
4. Replace `tests/fixtures/storquest_tracy_sample.html` with a real saved
   response (trim it if needed, but keep it real) and update
   `tests/test_storquest_parser.py` to match the corrected parser output.
5. Stop there. Do not add a database, a second facility, a second
   provider, Pydantic models, or anything from later phases unless I
   explicitly ask.

## Ground rules while working on this

- Before writing code for a step, briefly tell me what you're about to do
  and which files you'll touch.
- Don't refactor files I haven't asked you to touch.
- After making changes, run `pytest tests/ -v` and show me the result.
- If something in `planning.md` seems relevant to solving the current
  step, it's fine to be informed by it — but flag it explicitly ("this
  matches planning.md's X pattern") rather than silently pulling in
  scope from later phases.
- If you think we should skip ahead to a later phase (e.g. "this really
  needs a database"), say so and ask — don't just build it.
