"""
Tests against the SYNTHETIC fixture (see fixtures/storquest_tracy_sample.html).

These confirm the fallback text-parser's logic works as designed — they do
NOT confirm the parser works against real StorQuest markup. Once a real
raw response has been saved (via scripts/scrape_facility.py), replace the
fixture with that real file and update these assertions to match.
"""
from pathlib import Path

from app.providers.storquest.parser import parse_facility_page

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "storquest_tracy_sample.html"


def test_parses_facility_name_and_address():
    html = FIXTURE_PATH.read_text(encoding="utf-8")
    result = parse_facility_page(html)

    assert "Tracy" in result["facility_name"]
    assert "225 Gandy Dancer" in result["address"]


def test_parses_expected_number_of_units():
    html = FIXTURE_PATH.read_text(encoding="utf-8")
    result = parse_facility_page(html)

    assert result["parse_strategy"] == "visible_text_fallback"
    assert len(result["units"]) == 2


def test_parses_unit_fields_correctly():
    html = FIXTURE_PATH.read_text(encoding="utf-8")
    result = parse_facility_page(html)
    small_unit = result["units"][0]

    assert small_unit["width_ft"] == 5
    assert small_unit["length_ft"] == 5
    assert small_unit["standard_price"] == 84
    assert small_unit["promo_price"] == 37
    assert "Ground-Level Access" in small_unit["features"]
    assert small_unit["availability_text"] == "Limited Availability"


def test_parses_second_unit_availability_count():
    html = FIXTURE_PATH.read_text(encoding="utf-8")
    result = parse_facility_page(html)
    large_unit = result["units"][1]

    assert large_unit["standard_price"] == 363
    assert large_unit["promo_price"] == 279
    assert "Only 2 Left!" in large_unit["availability_text"]
