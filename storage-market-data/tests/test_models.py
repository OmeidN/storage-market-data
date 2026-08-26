"""Validation-layer tests: parser dicts become Pydantic models or raise."""
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.models import (
    AssetType,
    AvailabilityStatus,
    Facility,
    FacilityPage,
    Listing,
    ParseStatus,
    PriceUnit,
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

    assert page.facility.asset_type == AssetType.SELF_STORAGE
    first = page.units[0]
    assert first.square_footage == 25
    assert first.price == 84
    assert first.price_unit == PriceUnit.PER_UNIT_PER_MONTH
    assert first.price_data_available is True
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


def test_warehouse_listing_round_trips_through_same_model():
    page = facility_page_from_parse(
        {
            "facility_name": "DTLA",
            "address": "100 Warehouse St",
            "parse_strategy": "html_swiper",
            "asset_type": "warehouse_industrial",
            "units": [
                {
                    "provider_unit_id": "K8",
                    "square_footage": 1900,
                    "price": 24,
                    "price_unit": "per_sqft_per_year",
                    "price_data_available": True,
                    "availability_text": "Now",
                    "attributes": {"size_tier": "large"},
                }
            ],
        },
        provider="readyspaces",
        slug="downtown-los-angeles",
        url="https://readyspaces.com/location/los-angeles/downtown-los-angeles/",
    )
    listing = page.listings[0]
    assert page.facility.asset_type == AssetType.WAREHOUSE_INDUSTRIAL
    assert isinstance(listing, Listing)
    assert listing.square_footage == 1900
    assert listing.price == 24
    assert listing.price_unit == PriceUnit.PER_SQFT_PER_YEAR
    assert listing.price_data_available is True
    assert listing.width_ft is None
    assert listing.identity_key == "K8"


def test_listing_without_published_price_is_valid():
    listing = Listing(
        provider_unit_id="K8",
        square_footage=1900,
        price=None,
        price_data_available=False,
        availability_status=AvailabilityStatus.AVAILABLE,
        availability_text="Contact for Pricing",
    )
    assert listing.price is None
    assert listing.price_unit is None
    assert listing.price_data_available is False


def test_published_price_still_required_when_available_flag_true():
    with pytest.raises(ValidationError):
        Listing(
            square_footage=1900,
            price=None,
            price_data_available=True,
            availability_status=AvailabilityStatus.AVAILABLE,
        )
