"""Collect → parse → validate → store for one or many facilities."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from pydantic import ValidationError

from app.collectors.http import RawResponse, fetch
from app.database.repository import save_observation
from app.logging import get_logger
from app.models import AssetType, FacilityPage, ParseStatus, facility_page_from_parse
from app.providers.readyspaces.facilities import READYSPACES_FACILITIES
from app.providers.readyspaces.parser import parse_facility_page as parse_readyspaces
from app.providers.storquest.facilities import STORQUEST_FACILITIES
from app.providers.targets import FacilityTarget
from app.providers.storquest.parser import parse_facility_page as parse_storquest
from app.raw_storage import save_raw

log = get_logger(__name__)

ALL_FACILITIES: tuple[FacilityTarget, ...] = (
    *STORQUEST_FACILITIES,
    *READYSPACES_FACILITIES,
)


@dataclass
class ScrapeOutcome:
    target: FacilityTarget
    page: FacilityPage | None = None
    error: BaseException | None = None


def _is_blocked(response: RawResponse) -> bool:
    if response.status_code in {403, 429, 503}:
        return True
    text = response.text.lower()
    return (
        "attention required! | cloudflare" in text
        or "sorry, you have been blocked" in text
        or "cf-error-details" in text
    )


def _collect(url: str, provider: str) -> RawResponse:
    response = fetch(url)
    if provider == "readyspaces" and _is_blocked(response):
        log.warning(
            "ReadySpaces HTTP blocked (%s); trying Playwright",
            response.status_code,
        )
        from app.collectors.playwright import fetch_with_browser

        response = fetch_with_browser(url)
    return response


def scrape_facility(target: FacilityTarget) -> FacilityPage:
    provider = target.provider
    response = _collect(target.url, provider)
    raw_path = save_raw(
        response, provider=provider, facility_slug=target.slug
    )
    log.info("Saved raw response for %s to %s", target.slug, raw_path)

    if response.status_code != 200:
        raise RuntimeError(
            f"HTTP {response.status_code} fetching {target.url}"
        )

    if provider == "readyspaces":
        parsed = parse_readyspaces(response.text)
        asset_type = AssetType.WAREHOUSE_INDUSTRIAL
    elif provider == "storquest":
        parsed = parse_storquest(response.text)
        asset_type = AssetType.SELF_STORAGE
    else:
        raise ValueError(f"unknown provider {provider}")

    scraped_at = datetime.fromtimestamp(response.fetched_at, tz=timezone.utc)
    page = facility_page_from_parse(
        parsed,
        provider=provider,
        slug=target.slug,
        url=target.url,
        scraped_at=scraped_at,
        asset_type=asset_type,
    )

    if page.parse_status == ParseStatus.OK and page.listings:
        save_observation(page, scraped_at=scraped_at, url=target.url)
        log.info(
            "Stored %d observations for %s", len(page.listings), target.slug
        )
    else:
        log.warning(
            "Not writing observations for %s (parse_status=%s, units=%d)",
            target.slug,
            page.parse_status,
            len(page.listings),
        )
    return page


def scrape_all(
    facilities: tuple[FacilityTarget, ...] | list[FacilityTarget] | None = None,
) -> list[ScrapeOutcome]:
    """
    Scrape each facility independently. A network/parse/validation failure
    is logged and the rest of the list still runs.
    """
    targets = list(facilities) if facilities is not None else list(ALL_FACILITIES)
    outcomes: list[ScrapeOutcome] = []
    for target in targets:
        try:
            page = scrape_facility(target)
            outcomes.append(ScrapeOutcome(target=target, page=page))
            log.info(
                "Finished %s: status=%s units=%d",
                target.slug,
                page.parse_status,
                len(page.units),
            )
        except (ValidationError, Exception) as exc:
            log.exception("Failed to scrape %s (%s)", target.slug, target.url)
            outcomes.append(ScrapeOutcome(target=target, error=exc))
    return outcomes
