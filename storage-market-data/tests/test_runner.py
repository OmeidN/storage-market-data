"""One facility failing must not halt the rest of the run."""
from __future__ import annotations

import time
from unittest.mock import MagicMock

from app.collectors.http import RawResponse
from app.models import ParseStatus
from app.pipeline import scrape_all
from app.providers.storquest.facilities import FacilityTarget


def test_broken_facility_does_not_halt_others(monkeypatch):
    targets = [
        FacilityTarget("ok-one", "https://example.com/ok-one"),
        FacilityTarget("broken", "https://example.com/broken"),
        FacilityTarget("ok-two", "https://example.com/ok-two"),
    ]

    def fake_fetch(url: str, *, respect_delay: bool = True) -> RawResponse:
        if "broken" in url:
            raise ConnectionError("simulated network failure")
        return RawResponse(
            url=url,
            status_code=200,
            text="<html></html>",
            fetched_at=time.time(),
        )

    def fake_parse(_html: str) -> dict:
        return {
            "facility_name": "Mock",
            "address": "1 Main",
            "parse_strategy": "next_data_json",
            "units": [
                {
                    "provider_unit_id": "u1",
                    "width_ft": 5,
                    "length_ft": 5,
                    "features": [],
                    "standard_price": 10,
                    "promo_price": 8,
                    "rentable_units_count": 9,
                    "availability_text": None,
                    "free_first_month": False,
                }
            ],
        }

    monkeypatch.setattr("app.pipeline.fetch", fake_fetch)
    monkeypatch.setattr("app.pipeline.parse_facility_page", fake_parse)
    monkeypatch.setattr("app.pipeline.save_raw", MagicMock())
    monkeypatch.setattr("app.pipeline.save_observation", MagicMock())

    outcomes = scrape_all(targets)

    assert len(outcomes) == 3
    assert outcomes[0].error is None
    assert outcomes[0].page is not None
    assert outcomes[0].page.parse_status == ParseStatus.OK
    assert outcomes[1].error is not None
    assert "simulated network failure" in str(outcomes[1].error)
    assert outcomes[2].error is None
    assert outcomes[2].page is not None
    assert outcomes[2].page.parse_status == ParseStatus.OK
