"""
Tests against a real saved StorQuest facility page (Tracy, CA).

The fixture is a live HTML snapshot from scripts/scrape_facility.py, not
a hand-built approximation. Assertions match the unit cards on that page
(sizes, standard vs promotional rates, features, scarcity copy).
"""
from pathlib import Path

from app.providers.storquest.parser import parse_facility_page

FIXTURE_PATH = (
    Path(__file__).parent
    / "fixtures"
    / "storquest"
    / "tracy-ca-225-gandy-dancer-drive.html"
)


def _parse():
    html = FIXTURE_PATH.read_text(encoding="utf-8")
    return parse_facility_page(html)


def test_parses_facility_name_and_address():
    result = _parse()

    assert "Tracy" in result["facility_name"]
    assert "225 Gandy Dancer" in result["address"]
    assert "95377" in result["address"]


def test_parses_expected_number_of_units():
    result = _parse()

    assert result["parse_strategy"] == "next_data_json"
    assert len(result["units"]) == 9999


def test_parses_small_ground_level_unit():
    result = _parse()
    unit = result["units"][0]

    assert unit["width_ft"] == 5
    assert unit["length_ft"] == 5
    assert unit["standard_price"] == 84
    assert unit["promo_price"] == 37
    assert "Ground-Level Access" in unit["features"]
    assert "Climate-Controlled Storage" not in unit["features"]
    assert unit["availability_text"] == "Limited Availability"
    assert unit["free_first_month"] is True


def test_parses_climate_controlled_flag():
    result = _parse()
    climate = next(
        u
        for u in result["units"]
        if u["width_ft"] == 5
        and u["length_ft"] == 5
        and "Climate-Controlled Storage" in u["features"]
    )

    assert climate["standard_price"] == 78
    assert climate["promo_price"] == 42
    assert "Ground-Level Access" in climate["features"]
    assert climate["availability_text"] == "Limited Availability"


def test_parses_drive_up_only_one_left():
    result = _parse()
    unit = next(
        u
        for u in result["units"]
        if "Drive-Up Access" in u["features"] and u["promo_price"] == 69
    )

    assert unit["width_ft"] == 5
    assert unit["length_ft"] == 10
    assert unit["standard_price"] == 116
    assert unit["availability_text"] == "Only 1 Left!"
    assert unit["free_first_month"] is False


def test_parses_vehicle_parking_unit():
    result = _parse()
    unit = next(u for u in result["units"] if "Vehicle Parking" in u["features"])

    assert unit["width_ft"] == 9
    assert unit["length_ft"] == 15
    assert unit["standard_price"] == 150
    assert unit["promo_price"] == 48
    assert unit["availability_text"] == "Only 2 Left!"


def test_parses_large_drive_up_unit():
    result = _parse()
    unit = next(
        u
        for u in result["units"]
        if u["width_ft"] == 10 and u["length_ft"] == 20
    )

    assert unit["standard_price"] == 363
    assert unit["promo_price"] == 279
    assert "Drive-Up Access" in unit["features"]
    assert unit["availability_text"] == "Only 2 Left!"


def test_no_scarcity_badge_when_several_units_remain():
    result = _parse()
    unit = next(
        u
        for u in result["units"]
        if u["width_ft"] == 5
        and u["length_ft"] == 10
        and u["promo_price"] == 59
    )

    assert unit["availability_text"] is None
    assert "Ground-Level Access" in unit["features"]
