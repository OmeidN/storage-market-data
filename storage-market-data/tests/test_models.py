"""Validation-layer tests: parser dicts become Pydantic models or raise."""
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.models import (
    AvailabilityStatus,
    Facility,
    FacilityPage,
    ParseStatus,
    Unit,
    facility_page_from_parse,
)
from app.providers.storquest.parser import parse_facility_page

FIXTURE_PATH = (
    Path(__file__).parent
    / "fixtures"
    / "storquest"
    / "tracy-ca-225-gandy-dancer-drive.html"
)
TRACY_URL = "https://www.storquest.com/self-storage/ca/tracy/225-gandy-dancer-drive"
TRACY_SLUG = "tracy-ca-225-gandy-dancer-drive"


def _facility(**overrides):
    data = dict(
        provider="storquest",
        slug="test-facility",
        url="https://www.storquest.com/self-storage/ca/test",
        name="Test",
        address="1 Main St",
    )
    data.update(overrides)
    return Facility(**data)


def _parsed_unit(**overrides):
    data = dict(
        provider_unit_id="unit-1",
        width_ft=5,
        length_ft=5,
        features=["Ground-Level Access"],
        standard_price=84,
        promo_price=37,
        rentable_units_count=5,
        availability_text="Limited Availability",
        free_first_month=True,
    )
    data.update(overrides)
    return data


def test_tracy_fixture_round_trips_into_models():
    html = FIXTURE_PATH.read_text(encoding="utf-8")
    parsed = parse_facility_page(html)
    page = facility_page_from_parse(
        parsed,
        provider="storquest",
        slug=TRACY_SLUG,
        url=TRACY_URL,
    )

    assert page.parse_status == ParseStatus.OK
    assert page.parse_strategy == "next_data_json"
    assert page.facility.name and "Tracy" in page.facility.name
    assert page.facility.address and "225 Gandy Dancer" in page.facility.address
    assert len(page.units) == 12
    assert all(unit.provider_unit_id for unit in page.units)
    assert all(unit.identity_key == unit.provider_unit_id for unit in page.units)

    first = page.units[0]
    assert first.width_ft == 5
    assert first.length_ft == 5
    assert first.standard_price == 84
    assert first.promo_price == 37
    assert first.availability_status == AvailabilityStatus.LIMITED
    assert first.availability_text == "Limited Availability"

    abundant = next(
        u
        for u in page.units
        if u.width_ft == 5 and u.length_ft == 10 and u.promo_price == 59
    )
    assert abundant.availability_status == AvailabilityStatus.AVAILABLE
    assert abundant.availability_text is None

    scarce = next(
        u for u in page.units if u.availability_text == "Only 1 Left!"
    )
    assert scarce.availability_status == AvailabilityStatus.LIMITED


def test_malformed_size_raises_validation_error():
    with pytest.raises(ValidationError):
        facility_page_from_parse(
            {
                "facility_name": "Bad",
                "address": "1 Main",
                "parse_strategy": "next_data_json",
                "units": [_parsed_unit(width_ft=None)],
            },
            provider="storquest",
            slug="bad",
            url="https://example.com/bad",
        )


def test_missing_prices_raises_validation_error():
    with pytest.raises(ValidationError):
        facility_page_from_parse(
            {
                "facility_name": "Bad",
                "address": "1 Main",
                "parse_strategy": "next_data_json",
                "units": [_parsed_unit(standard_price=None, promo_price=None)],
            },
            provider="storquest",
            slug="bad",
            url="https://example.com/bad",
        )


def test_parser_found_nothing_is_not_sold_out():
    empty = facility_page_from_parse(
        {
            "facility_name": "Empty",
            "address": "1 Main",
            "parse_strategy": "next_data_json",
            "units": [],
        },
        provider="storquest",
        slug="empty",
        url="https://example.com/empty",
    )
    failed = facility_page_from_parse(
        {
            "facility_name": "Failed",
            "address": "1 Main",
            "parse_strategy": None,
            "units": None,
        },
        provider="storquest",
        slug="failed",
        url="https://example.com/failed",
    )
    sold_out = FacilityPage(
        parse_status=ParseStatus.OK,
        parse_strategy="next_data_json",
        facility=_facility(slug="sold-out", url="https://example.com/sold-out"),
        units=[
            Unit(
                width_ft=10,
                length_ft=10,
                standard_price=100,
                promo_price=80,
                availability_status=AvailabilityStatus.SOLD_OUT,
                availability_text="Sold Out",
            )
        ],
    )

    assert empty.parse_status == ParseStatus.NO_UNITS
    assert empty.units == []
    assert failed.parse_status == ParseStatus.FAILED
    assert failed.units == []
    assert sold_out.parse_status == ParseStatus.OK
    assert [u.availability_status for u in sold_out.units] == [
        AvailabilityStatus.SOLD_OUT
    ]
    assert empty.parse_status != sold_out.parse_status
    assert failed.parse_status != sold_out.parse_status
    assert empty.observations() == []
    assert failed.observations() == []
    assert sold_out.observations() == []  # no scraped_at yet
