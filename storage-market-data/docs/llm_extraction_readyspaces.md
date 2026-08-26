# ReadySpaces LLM extraction prototype (Milestone 6 Step 4)

The hand-written parser in `app/providers/readyspaces/parser.py` is the
**production scrape path**. This document is a comparison, not a cutover.

## Setup

```bash
pip install -e ".[llm]"
# GEMINI_API_KEY in the environment only — never git, never CI
python scripts/compare_llm_parser.py
```

Default model: `gemini-2.5-flash-lite` (plan default; override with
`GEMINI_MODEL`). If that id is retired, try `gemini-3.5-flash-lite`.
List prices at time of writing: about $0.10 / $0.40 per million
input/output tokens.

## What was compared

Same three fixtures as the parser tests:

| Facility | Fixture |
|---|---|
| Downtown LA | `tests/fixtures/readyspaces/los-angeles-downtown-los-angeles.html` |
| Redmond | `tests/fixtures/readyspaces/seattle-redmond.html` |
| South Gate | `tests/fixtures/readyspaces/los-angeles-south-gate.html` |

Parser extracts unit id, sqft, availability text, size tier. Price is
always null (`price_data_available = false`).

## Results

Run `python scripts/compare_llm_parser.py` with `GEMINI_API_KEY` set.
If the key is missing, the script prints parser output only and does
not call Gemini.

| Facility | Parser units | LLM units | Latency | Input tokens | Output tokens | Est. cost | Notes |
|---|---|---|---|---|---|---|---|
| Downtown LA | 7 | _pending key_ | | | | | Spot-checked vs live page: K8 is 1900 sq ft, Contact for Pricing |
| Redmond | 2 | _pending key_ | | | | | D3 850 / E4 1000 |
| South Gate | 19 | _pending key_ | | | | | G3 3000 enterprise |

Where parser and LLM disagree, the live page (unit slider: id, size,
availability) is the source of truth — not the model.

## Decision

**Keep the hand-written parser** as production. A Milestone 6 close-out
run on 2026-08-25 had no `GEMINI_API_KEY`, so the results table above
is parser-only (7 / 2 / 19 units). Fill it in later with
`python scripts/compare_llm_parser.py`; do not cut over automatically.

LLM extraction is a fallback prototype for markup that may drift; it is
not wired into `scrape_facility.py`.
