"""
Parser for a single StorQuest facility page.

⚠️ IMPORTANT — READ BEFORE TRUSTING THIS FILE ⚠️

This parser was written from a text-extraction preview of the Tracy, CA
page (https://www.storquest.com/self-storage/ca/tracy/225-gandy-dancer-drive),
NOT from inspecting the real raw HTML/DOM. It has not been run against a
real saved response.

It tries two strategies, in order:

1. `_parse_next_data()` — StorQuest's site is built on Next.js. Next.js
   apps commonly embed a `<script id="__NEXT_DATA__" type="application/json">`
   tag containing the exact JSON props used to render the page. If present,
   this is far more reliable than scraping visible text, since it won't
   break when the CSS/markup changes. THIS IS UNVERIFIED — the real page
   needs to be inspected to confirm the tag exists and to map its actual
   field names (they will almost certainly differ from the guesses below).

2. `_parse_visible_text()` — a fallback that walks the page's visible text
   in document order and pattern-matches on the sequence: unit size ->
   features -> "Standard Rate" -> price -> "Promotional Rate" -> price ->
   availability text. This mirrors the order units appeared in when the
   page was fetched during planning, but line breaks and ordering in the
   REAL DOM may differ once you inspect it directly.

Your first task with this file (see CURSOR_INSTRUCTIONS.md) is to run the
collector against the live page, open the saved raw HTML, and correct
whichever assumptions here are wrong.
"""
from __future__ import annotations

import json
import re
from typing import Any

from bs4 import BeautifulSoup

from app.logging import get_logger

log = get_logger(__name__)

SIZE_PATTERN = re.compile(r"(\d+)\s*['’]\s*x\s*(\d+)\s*['’]", re.IGNORECASE)
PRICE_PATTERN = re.compile(r"\$([\d,]+)\s*/\s*month", re.IGNORECASE)
KNOWN_FEATURES = {
    "Ground-Level Access",
    "Climate-Controlled Storage",
    "Drive-Up Access",
    "Vehicle Parking",
    "Indoor Access",
}
AVAILABILITY_PATTERNS = re.compile(
    r"(Limited Availability|Only \d+ Left!?|Sold Out)", re.IGNORECASE
)


def parse_facility_page(html: str) -> dict[str, Any]:
    """
    Parse a StorQuest facility page into a plain dict. Returns everything
    found — does not validate or normalize (that's Phase 3, with Pydantic
    models, not this file).
    """
    soup = BeautifulSoup(html, "lxml")

    result: dict[str, Any] = {
        "facility_name": _extract_facility_name(soup),
        "address": _extract_address(soup),
        "units": None,
        "parse_strategy": None,
    }

    next_data_units = _parse_next_data(soup)
    if next_data_units is not None:
        result["units"] = next_data_units
        result["parse_strategy"] = "next_data_json"
        return result

    log.warning(
        "__NEXT_DATA__ not found or didn't match expected shape — "
        "falling back to visible-text parsing. This fallback is more "
        "fragile and should be treated as a stopgap, not the long-term approach."
    )
    result["units"] = _parse_visible_text(soup)
    result["parse_strategy"] = "visible_text_fallback"
    return result


def _extract_facility_name(soup: BeautifulSoup) -> str | None:
    if soup.title and soup.title.string:
        return soup.title.string.strip()
    h1 = soup.find("h1")
    return h1.get_text(strip=True) if h1 else None


def _extract_address(soup: BeautifulSoup) -> str | None:
    text = soup.get_text(" ", strip=True)
    # e.g. "225 Gandy Dancer Drive Tracy, CA, 95377"
    match = re.search(
        r"\d+\s+[A-Za-z0-9.\- ]+?\s+[A-Za-z .]+,\s*[A-Z]{2},?\s*\d{5}", text
    )
    return match.group(0) if match else None


def _parse_next_data(soup: BeautifulSoup) -> list[dict[str, Any]] | None:
    """
    UNVERIFIED. Look for Next.js's standard data-injection script tag and
    try a couple of plausible key paths for unit/pricing data. Almost
    certainly needs correcting once you've seen the real JSON shape —
    print(json.dumps(data, indent=2)) and look for the units array yourself.
    """
    tag = soup.find("script", id="__NEXT_DATA__")
    if not tag or not tag.string:
        return None

    try:
        data = json.loads(tag.string)
    except json.JSONDecodeError:
        log.warning("__NEXT_DATA__ tag found but was not valid JSON")
        return None

    # Guesses at where unit data might live — verify and fix against the
    # real payload. Common Next.js shapes nest page props under
    # data["props"]["pageProps"][...].
    page_props = data.get("props", {}).get("pageProps", {})
    for key in ("units", "unitTypes", "availableUnits", "facility"):
        if key in page_props:
            log.info("Found candidate key '%s' in __NEXT_DATA__ pageProps", key)
            # Returning None here on purpose — we found *a* candidate but
            # haven't verified its shape enough to safely map it to our
            # unit dict format. Do that mapping once you've inspected it.
            return None

    return None


def _parse_visible_text(soup: BeautifulSoup) -> list[dict[str, Any]]:
    """
    Fallback: scan visible text in document order. Fragile by nature —
    treat any output from this as needing a manual spot-check against the
    live page, not as trustworthy on its own.
    """
    lines = [
        line.strip()
        for line in soup.get_text("\n", strip=True).split("\n")
        if line.strip()
    ]

    units: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    expecting_price_for: str | None = None  # "standard" or "promo"

    for line in lines:
        size_match = SIZE_PATTERN.search(line)
        if size_match and ("x" in line.lower() or "×" in line):
            if current:
                units.append(current)
            current = {
                "width_ft": int(size_match.group(1)),
                "length_ft": int(size_match.group(2)),
                "features": [],
                "standard_price": None,
                "promo_price": None,
                "availability_text": None,
                "free_first_month": False,
            }
            expecting_price_for = None
            continue

        if current is None:
            continue

        if line in KNOWN_FEATURES:
            current["features"].append(line)
            continue

        if line.lower() == "standard rate":
            expecting_price_for = "standard"
            continue

        if line.lower() == "promotional rate":
            expecting_price_for = "promo"
            continue

        price_match = PRICE_PATTERN.search(line)
        if price_match and expecting_price_for:
            price = int(price_match.group(1).replace(",", ""))
            if expecting_price_for == "standard":
                current["standard_price"] = price
            else:
                current["promo_price"] = price
            expecting_price_for = None
            continue

        if "free first month" in line.lower():
            current["free_first_month"] = True
            continue

        availability_match = AVAILABILITY_PATTERNS.search(line)
        if availability_match:
            current["availability_text"] = availability_match.group(0)
            continue

    if current:
        units.append(current)

    return units
