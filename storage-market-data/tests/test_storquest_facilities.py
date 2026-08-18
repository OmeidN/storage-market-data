"""Parser tests against a real saved HTML fixture per StorQuest facility."""
from pathlib import Path

import pytest

from app.models import ParseStatus, facility_page_from_parse
from app.providers.storquest.facilities import STORQUEST_FACILITIES
from app.providers.storquest.parser import parse_facility_page

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "storquest"


def _page(slug: str):
    target = next(t for t in STORQUEST_FACILITIES if t.slug == slug)
    html = (FIXTURE_DIR / f"{slug}.html").read_text(encoding="utf-8")
    return facility_page_from_parse(
        parse_facility_page(html),
        provider="storquest",
        slug=slug,
        url=target.url,
    )


@pytest.mark.parametrize(
    "target",
    STORQUEST_FACILITIES,
    ids=[f.slug for f in STORQUEST_FACILITIES],
)
def test_facility_fixture_parses(target):
    path = FIXTURE_DIR / f"{target.slug}.html"
    assert path.exists(), f"missing fixture {path}"
    html = path.read_text(encoding="utf-8")
    page = facility_page_from_parse(
        parse_facility_page(html),
        provider="storquest",
        slug=target.slug,
        url=target.url,
    )
    assert page.parse_status == ParseStatus.OK
    assert page.parse_strategy == "next_data_json"
    assert page.units, f"{target.slug} parsed with no units"
    for unit in page.units:
        assert unit.width_ft > 0
        assert unit.length_ft > 0
        assert unit.standard_price is not None or unit.promo_price is not None
        assert unit.identity_key


def test_anaheim_small_drive_up_unit():
    page = _page("anaheim-ca-1431-s-sunkist-street")
    assert "Anaheim" in (page.facility.name or "")
    assert "1431 S Sunkist" in (page.facility.address or "")
    assert len(page.units) == 16
    unit = next(
        u
        for u in page.units
        if u.width_ft == 5 and u.length_ft == 7 and "Drive-Up Access" in u.features
    )
    assert unit.standard_price == 86
    assert unit.promo_price == 56
    assert unit.availability_text == "Only 1 Left!"


def test_arlington_same_size_units_stay_distinct():
    page = _page("arlington-tx-1830-east-division-street")
    assert "Arlington" in (page.facility.name or "")
    fives = [
        u for u in page.units if u.width_ft == 5 and u.length_ft == 5
    ]
    assert len(fives) >= 3
    keys = {u.identity_key for u in fives}
    assert len(keys) == len(fives)
    ground = next(u for u in fives if "Ground-Level Access" in u.features)
    assert ground.standard_price == 50
    assert ground.promo_price == 23


def test_apopka_is_vehicle_parking():
    page = _page("apopka-fl-2371-south-orange-blossom-trail")
    assert "Apopka" in (page.facility.name or "")
    assert len(page.units) == 7
    assert all("Vehicle Parking" in u.features for u in page.units)
    covered = next(
        u
        for u in page.units
        if u.width_ft == 12 and u.length_ft == 25 and u.promo_price == 185
    )
    assert covered.standard_price is None
    assert "Covered Parking" in covered.features
