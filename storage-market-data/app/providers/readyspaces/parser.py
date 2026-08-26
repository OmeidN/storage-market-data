"""
Parser for a single ReadySpaces facility page.

Inventory is server-rendered in `.available-units-slider .swiper-slide`
(unit id, sqft, availability date/now, data-size tier). Price is always
"Contact for Pricing" — see MILESTONE_6_PLAN.md. ReadySpaces listing
pages only show available units, so confirmed SOLD_OUT will not appear
here; rental velocity for this provider is inferred-only.
"""
from __future__ import annotations

import re

from bs4 import BeautifulSoup

from app.logging import get_logger

log = get_logger(__name__)

SQFT_RE = re.compile(r"(\d[\d,]*)\s*sq\s*ft", re.IGNORECASE)
CLEAR_HEIGHT_RE = re.compile(r"(\d+)\s*['’]?\s*clear height", re.IGNORECASE)
DOCK_RE = re.compile(r"(\d+)\s*dock-high doors", re.IGNORECASE)
DRIVE_IN_RE = re.compile(r"(\d+)\s*drive-in bays", re.IGNORECASE)
UNIT_ID_RE = re.compile(r"Unit\s+([A-Za-z0-9-]+)", re.IGNORECASE)


def _is_cloudflare_block(html: str) -> bool:
    lowered = html.lower()
    return (
        "attention required! | cloudflare" in lowered
        or "sorry, you have been blocked" in lowered
        or "cf-error-details" in lowered
    )


def _facility_attributes(text: str) -> dict:
    attrs: dict = {}
    height = CLEAR_HEIGHT_RE.search(text)
    if height:
        attrs["clear_height_ft"] = int(height.group(1))
    docks = DOCK_RE.search(text)
    if docks:
        attrs["dock_doors"] = int(docks.group(1))
    drive_in = DRIVE_IN_RE.search(text)
    if drive_in:
        attrs["drive_in_bays"] = int(drive_in.group(1))
    return attrs


def _availability_text(slide_text: str) -> str | None:
    match = re.search(
        r"Availability:\s*([A-Za-z0-9/]+(?:/\d{4})?)",
        slide_text,
        re.IGNORECASE,
    )
    if not match:
        return None
    return match.group(1).strip()


def parse_facility_page(html: str) -> dict:
    if _is_cloudflare_block(html):
        log.warning("ReadySpaces response looks like a Cloudflare block")
        return {
            "facility_name": None,
            "address": None,
            "parse_strategy": None,
            "asset_type": "warehouse_industrial",
            "facility_attributes": {},
            "units": None,
        }

    soup = BeautifulSoup(html, "lxml")
    title = soup.title.get_text(" ", strip=True) if soup.title else None
    h1 = soup.find("h1")
    name = h1.get_text(" ", strip=True) if h1 else title

    address_el = soup.select_one("p.address")
    address = address_el.get_text(" ", strip=True) if address_el else None
    if not address:
        for candidate in soup.find_all(["p", "div", "span"]):
            text = candidate.get_text(" ", strip=True)
            if re.search(r"\d{5}", text) and len(text) < 120:
                address = text
                break

    infra_el = soup.select_one(".location-infrastructure")
    infra_text = infra_el.get_text(" ", strip=True) if infra_el else soup.get_text(" ", strip=True)
    facility_attributes = _facility_attributes(infra_text)

    slides = soup.select(".available-units-slider .swiper-slide")
    units: list[dict] = []
    seen: set[str] = set()
    for slide in slides:
        classes = slide.get("class") or []
        if "swiper-slide-duplicate" in classes:
            continue
        text = slide.get_text(" ", strip=True)
        bold = slide.select_one("b.block.text-xl") or slide.find("b")
        raw_id = bold.get_text(" ", strip=True) if bold else ""
        match = UNIT_ID_RE.search(raw_id or text)
        provider_unit_id = match.group(1) if match else (raw_id or None)
        if not provider_unit_id:
            continue
        if provider_unit_id in seen:
            continue
        sqft_match = SQFT_RE.search(text)
        if not sqft_match:
            continue
        square_footage = int(sqft_match.group(1).replace(",", ""))
        seen.add(provider_unit_id)
        avail = _availability_text(text)
        size_tier = slide.get("data-size")
        units.append(
            {
                "provider_unit_id": provider_unit_id,
                "square_footage": square_footage,
                "price": None,
                "price_unit": None,
                "price_data_available": False,
                "availability_text": avail,
                "availability_status": "AVAILABLE",
                "attributes": {
                    "size_tier": size_tier,
                    "listed_as": raw_id or f"Unit {provider_unit_id}",
                },
            }
        )

    if not slides:
        log.warning("ReadySpaces page had no available-units slider")
        return {
            "facility_name": name,
            "address": address,
            "parse_strategy": None,
            "asset_type": "warehouse_industrial",
            "facility_attributes": facility_attributes,
            "units": None,
        }

    return {
        "facility_name": name,
        "address": address,
        "parse_strategy": "html_swiper",
        "asset_type": "warehouse_industrial",
        "facility_attributes": facility_attributes,
        "units": units,
    }
