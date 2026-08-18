"""Collect → parse → validate → store for one or many StorQuest facilities."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from pydantic import ValidationError

from app.collectors.http import fetch
from app.database.repository import save_observation
from app.logging import get_logger
from app.models import FacilityPage, ParseStatus, facility_page_from_parse
from app.providers.storquest.facilities import STORQUEST_FACILITIES, FacilityTarget
from app.providers.storquest.parser import parse_facility_page
from app.raw_storage import save_raw

log = get_logger(__name__)


@dataclass
class ScrapeOutcome:
    target: FacilityTarget
    page: FacilityPage | None = None
    error: BaseException | None = None


def scrape_facility(target: FacilityTarget) -> FacilityPage:
    response = fetch(target.url)
    raw_path = save_raw(
        response, provider="storquest", facility_slug=target.slug
    )
    log.info("Saved raw response for %s to %s", target.slug, raw_path)

    if response.status_code != 200:
        raise RuntimeError(
            f"HTTP {response.status_code} fetching {target.url}"
        )

    parsed = parse_facility_page(response.text)
    scraped_at = datetime.fromtimestamp(response.fetched_at, tz=timezone.utc)
    page = facility_page_from_parse(
        parsed,
        provider="storquest",
        slug=target.slug,
        url=target.url,
        scraped_at=scraped_at,
    )

    if page.parse_status == ParseStatus.OK and page.units:
        save_observation(page, scraped_at=scraped_at, url=target.url)
        log.info(
            "Stored %d observations for %s", len(page.units), target.slug
        )
    else:
        log.warning(
            "Not writing observations for %s (parse_status=%s, units=%d)",
            target.slug,
            page.parse_status,
            len(page.units),
        )
    return page


def scrape_all(
    facilities: tuple[FacilityTarget, ...] | list[FacilityTarget] | None = None,
) -> list[ScrapeOutcome]:
    """
    Scrape each facility independently. A network/parse/validation failure
    is logged and the rest of the list still runs.
    """
    targets = list(facilities) if facilities is not None else list(STORQUEST_FACILITIES)
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
