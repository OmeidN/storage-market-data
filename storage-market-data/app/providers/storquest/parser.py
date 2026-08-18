"""
Parser for a single StorQuest facility page.

Verified against the live Tracy, CA page
(https://www.storquest.com/self-storage/ca/tracy/225-gandy-dancer-drive).

StorQuest is a Next.js App Router site. There is no
`<script id="__NEXT_DATA__">` tag (that's Pages Router). Unit/pricing
data is instead embedded in `self.__next_f.push(...)` RSC payloads, in a
dehydrated TanStack Query cache keyed `LOCATION_UNIT_GROUPS`. That JSON
is the primary extraction path.

Visible-text parsing remains as a fallback only. On the real page it is
unreliable: unit sizes are split across HTML comments (`5<!-- -->' x <!-- -->5`)
so a line-oriented regex never sees a complete `5' x 5'`.
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

# Next.js App Router serializes RSC chunks as self.__next_f.push([1, "..."]).
_NEXT_F_PUSH = re.compile(
    r"self\.__next_f\.push\(\[1,(.*)\]\)\s*$",
    re.DOTALL,
)

# Scarcity copy on the live unit cards is not a field in the JSON.
# These thresholds were inferred from the Tracy snapshot: 1–2 →
# "Only N Left!", 3–5 → "Limited Availability", 6+ → no badge.
_LIMITED_AVAILABILITY_MAX = 5
_ONLY_N_LEFT_MAX = 2


def parse_facility_page(html: str) -> dict[str, Any]:
    """
    Parse a StorQuest facility page into a plain dict. Validation and
    normalization happen in app.models.facility_page_from_parse, not here.
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
        "Embedded Next.js unit JSON not found or didn't match expected "
        "shape — falling back to visible-text parsing. This fallback is more "
        "fragile and should be treated as a stopgap, not the long-term approach."
    )
    result["units"] = _parse_visible_text(soup)
    result["parse_strategy"] = "visible_text_fallback"
    return result


def _json_ld_objects(soup: BeautifulSoup) -> list[dict[str, Any]]:
    objects: list[dict[str, Any]] = []
    for tag in soup.find_all("script", type="application/ld+json"):
        if not tag.string:
            continue
        try:
            data = json.loads(tag.string)
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict):
            objects.append(data)
        elif isinstance(data, list):
            objects.extend(item for item in data if isinstance(item, dict))
    return objects


def _extract_facility_name(soup: BeautifulSoup) -> str | None:
    if soup.title and soup.title.string:
        return soup.title.string.strip()
    for data in _json_ld_objects(soup):
        name = data.get("name")
        if data.get("@type") == "SelfStorage" and isinstance(name, str) and name.strip():
            return name.strip()
    h1 = soup.find("h1")
    return h1.get_text(strip=True) if h1 else None


def _extract_address(soup: BeautifulSoup) -> str | None:
    for data in _json_ld_objects(soup):
        addr = data.get("address")
        if not isinstance(addr, dict):
            continue
        street = addr.get("streetAddress")
        city = addr.get("addressLocality")
        region = addr.get("addressRegion")
        postal = addr.get("postalCode")
        if not street:
            continue
        locality = ", ".join(part for part in (city, region) if part)
        if postal:
            locality = f"{locality} {postal}".strip() if locality else postal
        return ", ".join(part for part in (street, locality) if part)

    text = soup.get_text(" ", strip=True)
    # e.g. "225 Gandy Dancer Drive Tracy, CA, 95377"
    match = re.search(
        r"\d+\s+[A-Za-z0-9.\- ]+?\s+[A-Za-z .]+,\s*[A-Z]{2},?\s*\d{5}", text
    )
    return match.group(0) if match else None


def _parse_next_data(soup: BeautifulSoup) -> list[dict[str, Any]] | None:
    """
    Pull unit groups out of embedded Next.js JSON.

    Pages Router (`__NEXT_DATA__`) is checked first in case StorQuest
    ever ships that shape. The live site uses App Router RSC (`__next_f`)
    with a LOCATION_UNIT_GROUPS query — that's the path that actually
    matches the Tracy page.
    """
    groups = _unit_groups_from_next_data_tag(soup)
    if groups is None:
        groups = _unit_groups_from_next_f(soup)
    if groups is None:
        return None
    return [_map_unit_group(group) for group in groups]


def _unit_groups_from_next_data_tag(soup: BeautifulSoup) -> list[dict[str, Any]] | None:
    tag = soup.find("script", id="__NEXT_DATA__")
    if not tag or not tag.string:
        return None
    try:
        data = json.loads(tag.string)
    except json.JSONDecodeError:
        log.warning("__NEXT_DATA__ tag found but was not valid JSON")
        return None
    return _find_unit_groups(data)


def _unit_groups_from_next_f(soup: BeautifulSoup) -> list[dict[str, Any]] | None:
    stream = _next_f_stream(soup)
    if not stream:
        return None

    for payload in _next_f_json_payloads(stream):
        groups = _find_unit_groups(payload)
        if groups is not None:
            return groups
    return None


def _next_f_stream(soup: BeautifulSoup) -> str:
    parts: list[str] = []
    for tag in soup.find_all("script"):
        text = tag.string
        if not text or "self.__next_f.push" not in text:
            continue
        match = _NEXT_F_PUSH.search(text)
        if not match:
            continue
        try:
            chunk = json.loads(match.group(1))
        except json.JSONDecodeError:
            continue
        if isinstance(chunk, str):
            parts.append(chunk)
    return "".join(parts)


def _next_f_json_payloads(stream: str) -> list[Any]:
    """
    Split an RSC flight stream into JSON payloads.

    Records look like `<id>:<json>` separated by newlines. Non-JSON
    records (module imports, hints, binary) are skipped.
    """
    payloads: list[Any] = []
    current_id: str | None = None
    buf: list[str] = []

    def flush() -> None:
        if current_id is None or not buf:
            return
        raw = "\n".join(buf)
        try:
            payloads.append(json.loads(raw))
        except json.JSONDecodeError:
            return

    for line in stream.split("\n"):
        match = re.match(r"^([0-9a-fA-F]+):(.*)$", line)
        if match:
            flush()
            current_id = match.group(1)
            buf = [match.group(2)]
        elif current_id is not None:
            buf.append(line)
    flush()
    return payloads


def _find_unit_groups(obj: Any) -> list[dict[str, Any]] | None:
    """
    Walk a JSON tree for the LOCATION_UNIT_GROUPS query, or any list of
    seUnitGroup objects.
    """
    found_by_key: list[dict[str, Any]] | None = None
    found_by_type: list[dict[str, Any]] | None = None

    def walk(node: Any) -> None:
        nonlocal found_by_key, found_by_type
        if found_by_key is not None:
            return
        if isinstance(node, dict):
            query_key = node.get("queryKey")
            if (
                isinstance(query_key, list)
                and query_key
                and query_key[0] == "LOCATION_UNIT_GROUPS"
            ):
                data = (node.get("state") or {}).get("data")
                if isinstance(data, list) and data and isinstance(data[0], dict):
                    found_by_key = data
                    return
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            if (
                found_by_type is None
                and node
                and all(isinstance(item, dict) for item in node)
                and any(item.get("_type") == "seUnitGroup" for item in node)
            ):
                found_by_type = node
            for item in node:
                walk(item)

    walk(obj)
    return found_by_key if found_by_key is not None else found_by_type


def _map_unit_group(group: dict[str, Any]) -> dict[str, Any]:
    features = [
        feature["title"]
        for feature in (group.get("features") or [])
        if isinstance(feature, dict) and feature.get("title")
    ]
    promo_description = group.get("promoPublicDescription") or ""
    rentable = _as_int(group.get("rentableUnitsCount"))
    return {
        "provider_unit_id": _provider_unit_id(group),
        "width_ft": _as_int(group.get("width")),
        "length_ft": _as_int(group.get("length")),
        "features": features,
        # On the live cards, "Standard Rate" is the struck-through
        # crossOutRate; "Promotional Rate" is price.
        "standard_price": _as_int(group.get("crossOutRate")),
        "promo_price": _as_int(group.get("price")),
        "rentable_units_count": rentable,
        "availability_text": _availability_text(rentable),
        "free_first_month": "free first month" in str(promo_description).lower(),
    }


def _provider_unit_id(group: dict[str, Any]) -> str | None:
    for key in ("unitId", "_id"):
        value = group.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _as_int(value: Any) -> int | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        try:
            return int(float(value.replace(",", "").replace("$", "")))
        except ValueError:
            return None
    return None


def _availability_text(rentable_count: Any) -> str | None:
    count = _as_int(rentable_count)
    if count is None:
        return None
    if count <= 0:
        return "Sold Out"
    if count <= _ONLY_N_LEFT_MAX:
        return f"Only {count} Left!"
    if count <= _LIMITED_AVAILABILITY_MAX:
        return "Limited Availability"
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
                "provider_unit_id": None,
                "width_ft": int(size_match.group(1)),
                "length_ft": int(size_match.group(2)),
                "features": [],
                "standard_price": None,
                "promo_price": None,
                "rentable_units_count": None,
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
