# Milestone 1 — One provider, one real facility

**Status:** closed  
**Commit:** `aa9f178` (initial skeleton; parser then proven against live StorQuest HTML)

---

## What was created, and why

Milestone 1 was the first vertical slice of the pipeline: **collect → save raw HTML → parse → print**, for a single StorQuest page (Tracy, CA). No database, no scheduler, no second facility.

The point was to prove that publicly listed unit sizes, prices, features, and availability could be extracted *correctly* from a real page — not from a guessed DOM. `planning.md` calls this the first complete path; everything later (history, velocity, comparison reports) is worthless if the parser is wrong.

**What shipped:**

- `app/collectors/http.py` — fetch one URL, return the body. No retries, no browser.
- `app/raw_storage.py` — write HTML to `data/raw/` so parsers can be developed offline.
- `app/providers/storquest/parser.py` — facility name/address plus units (size, standard/promo price, climate/drive-up/ground-level/vehicle flags, availability text).
- `scripts/scrape_facility.py` — collector → save → parse → print JSON.
- Config, logging, `pyproject.toml`, pytest, `.env.example`.

The first parser draft was written from a text preview and flagged unverified. Against the real saved page, unit data lived in Next.js RSC JSON, not a `__NEXT_DATA__` script tag. The parser was rewritten around that JSON (visible-text as fallback) until output matched the live Tracy listing.

`robots.txt` was reviewed before collection: `/self-storage/...` is allowed; `/studio/` is the CMS. A request delay stayed in place as a courtesy even though no crawl-delay was set.

## What was tested, and the results

| Check | Result |
|---|---|
| Live fetch of the Tracy URL | Succeeded; HTML landed in `data/raw/` |
| Parser vs live page (~12 units) | Sizes, standard vs promo, flags, and scarcity text matched |
| Fixture tests | Synthetic fixture replaced with real saved Tracy HTML; `tests/test_storquest_parser.py` updated to that snapshot |
| `pytest tests/ -v` | Passed (parser-only suite; no Postgres yet) |

Parser tests run offline against the saved fixture. They freeze a moment in time — they do not re-hit StorQuest.

## How this contributes to the bigger picture

The product is a **decision-support tool for acquisition teams**, not an operator pricing dashboard. The flagship number is **rental velocity** (average days-to-lease), which only exists if we can watch the same unit over time. That starts with one honest observation of one real facility.

Milestone 1 also locked in the architecture that later milestones still use:

- Collect separately from parse (raw HTML can be replayed).
- Provider-specific code lives under `providers/storquest/`.
- Never treat a failed fetch as “sold out” — there was nothing to persist yet, but the invariant was already the rule.

Without this slice, there is no history to store (M2), nothing to run unattended (M4), and nothing for the warehouse to turn into velocity (M5) or a client comparison (M7).
