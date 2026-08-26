"""Parser tests against a real saved HTML fixture per ReadySpaces facility."""
from pathlib import Path

import pytest

from app.models import (
    AssetType,
    AvailabilityStatus,
    ParseStatus,
    facility_page_from_parse,
)
from app.providers.readyspaces.facilities import READYSPACES_FACILITIES
from app.providers.readyspaces.parser import parse_facility_page

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "readyspaces"


def _page(slug: str):
    target = next(t for t in READYSPACES_FACILITIES if t.slug == slug)
    html = (FIXTURE_DIR / f"{slug}.html").read_text(encoding="utf-8")
    return facility_page_from_parse(
        parse_facility_page(html),
        provider="readyspaces",
        slug=slug,
        url=target.url,
        asset_type=AssetType.WAREHOUSE_INDUSTRIAL,
    )


@pytest.mark.parametrize(
    "target",
    READYSPACES_FACILITIES,
    ids=[f.slug for f in READYSPACES_FACILITIES],
)
def test_facility_fixture_parses(target):
    path = FIXTURE_DIR / f"{target.slug}.html"
    assert path.exists(), f"missing fixture {path}"
    html = path.read_text(encoding="utf-8")
    page = facility_page_from_parse(
        parse_facility_page(html),
        provider="readyspaces",
        slug=target.slug,
        url=target.url,
        asset_type=AssetType.WAREHOUSE_INDUSTRIAL,
    )
    assert page.parse_status == ParseStatus.OK
    assert page.parse_strategy == "html_swiper"
    assert page.facility.asset_type == AssetType.WAREHOUSE_INDUSTRIAL
    assert page.listings
    for listing in page.listings:
        assert listing.square_footage > 0
        assert listing.price is None
        assert listing.price_data_available is False
        assert listing.identity_key
        assert listing.availability_status == AvailabilityStatus.AVAILABLE


def test_dtla_unit_k8_is_1900_sqft():
    page = _page("los-angeles-downtown-los-angeles")
    assert "Lincoln Heights" in (page.facility.name or "") or "Downtown" in (
        page.facility.name or ""
    )
    assert page.facility.address and "1919 Vineburn" in page.facility.address
    k8 = next(u for u in page.listings if u.provider_unit_id == "K8")
    assert k8.square_footage == 1900
    assert k8.price is None
    assert k8.price_data_available is False
    assert k8.attributes.get("size_tier") == "large"
    assert page.facility.attributes.get("clear_height_ft") == 13
    assert page.facility.attributes.get("dock_doors") == 16


def test_redmond_units_have_no_published_price():
    page = _page("seattle-redmond")
    assert page.facility.address and "15300 Redmond-Woodinville" in page.facility.address
    ids = {u.provider_unit_id for u in page.listings}
    assert {"D3", "E4"} <= ids
    assert all(u.price is None and u.price_data_available is False for u in page.listings)
    assert page.facility.attributes.get("clear_height_ft") == 24


def test_south_gate_g3_is_enterprise_3000():
    page = _page("los-angeles-south-gate")
    assert page.facility.address and "5625 Firestone" in page.facility.address
    g3 = next(u for u in page.listings if u.provider_unit_id == "G3")
    assert g3.square_footage == 3000
    assert g3.attributes.get("size_tier") == "enterprise"
    assert len(page.listings) >= 10
