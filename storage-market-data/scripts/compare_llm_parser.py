"""
Compare Gemini extraction against the hand-written ReadySpaces parser.

Prototype only — the parser remains the production scrape path.
Requires GEMINI_API_KEY. Never commit the key.

Usage:
    python scripts/compare_llm_parser.py
"""
from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path

from bs4 import BeautifulSoup

from app.providers.readyspaces.facilities import READYSPACES_FACILITIES
from app.providers.readyspaces.parser import parse_facility_page

PROJECT_ROOT = Path(__file__).resolve().parent.parent
FIXTURE_DIR = PROJECT_ROOT / "tests" / "fixtures" / "readyspaces"
MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")

PROMPT = """Extract warehouse listings from this ReadySpaces facility page text.
Return JSON only, no markdown:
{
  "facility_name": string or null,
  "address": string or null,
  "listings": [
    {
      "provider_unit_id": string,
      "square_footage": integer,
      "availability_text": string or null,
      "size_tier": string or null
    }
  ]
}
Price is never published on this site. Do not invent prices or units.
Page text:
"""


def _clean_text(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "noscript", "svg", "picture"]):
        tag.decompose()
    text = soup.get_text("\n", strip=True)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text[:12000]


def _parser_summary(parsed: dict) -> dict:
    units = parsed.get("units") or []
    return {
        "facility_name": parsed.get("facility_name"),
        "address": parsed.get("address"),
        "listings": [
            {
                "provider_unit_id": u.get("provider_unit_id"),
                "square_footage": u.get("square_footage"),
                "availability_text": u.get("availability_text"),
                "size_tier": (u.get("attributes") or {}).get("size_tier"),
            }
            for u in units
        ],
    }


def _extract_json(text: str) -> dict:
    raw = text.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
    return json.loads(raw)


def main() -> None:
    key = os.getenv("GEMINI_API_KEY", "").strip()
    if not key:
        print("GEMINI_API_KEY is not set. Parser-only summary follows; no LLM call.")
        for target in READYSPACES_FACILITIES:
            html = (FIXTURE_DIR / f"{target.slug}.html").read_text(encoding="utf-8")
            parsed = parse_facility_page(html)
            print(target.slug, json.dumps(_parser_summary(parsed), indent=2))
        return

    from google import genai

    client = genai.Client(api_key=key)
    rows = []
    for target in READYSPACES_FACILITIES:
        html = (FIXTURE_DIR / f"{target.slug}.html").read_text(encoding="utf-8")
        parser_out = _parser_summary(parse_facility_page(html))
        cleaned = _clean_text(html)
        started = time.perf_counter()
        response = client.models.generate_content(
            model=MODEL,
            contents=PROMPT + cleaned,
        )
        latency_s = time.perf_counter() - started
        usage = getattr(response, "usage_metadata", None)
        llm_text = getattr(response, "text", None) or ""
        try:
            llm_out = _extract_json(llm_text)
        except json.JSONDecodeError:
            llm_out = {"raw": llm_text[:2000]}
        parser_ids = {u["provider_unit_id"] for u in parser_out["listings"]}
        llm_ids = {u.get("provider_unit_id") for u in llm_out.get("listings") or []}
        rows.append(
            {
                "slug": target.slug,
                "model": MODEL,
                "latency_s": round(latency_s, 3),
                "input_tokens": getattr(usage, "prompt_token_count", None) if usage else None,
                "output_tokens": getattr(usage, "candidates_token_count", None) if usage else None,
                "parser_unit_count": len(parser_out["listings"]),
                "llm_unit_count": len(llm_out.get("listings") or []),
                "ids_only_in_parser": sorted(parser_ids - llm_ids),
                "ids_only_in_llm": sorted(x for x in (llm_ids - parser_ids) if x),
                "parser": parser_out,
                "llm": llm_out,
            }
        )
        print(json.dumps(rows[-1], indent=2)[:2000])
        print("---")

    out = PROJECT_ROOT / "docs" / "llm_extraction_readyspaces.last.json"
    out.write_text(json.dumps(rows, indent=2), encoding="utf-8")
    print("wrote", out)


if __name__ == "__main__":
    main()
