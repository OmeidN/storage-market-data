"""
The simplest possible collector: given a URL, return the raw response.

Deliberately does NOT parse, retry, rate-limit across calls, or know
anything about "facilities" or "providers". Collection and parsing are
kept separate on purpose — see planning.md § "Separate Collection From
Parsing". If a provider later turns out to need Playwright instead of
plain HTTP, that's a new collector, not a rewrite of this one.
"""
from __future__ import annotations

import time
from dataclasses import dataclass

import httpx

from app.config import settings
from app.logging import get_logger

log = get_logger(__name__)


@dataclass
class RawResponse:
    url: str
    status_code: int
    text: str
    fetched_at: float


def fetch(url: str, *, respect_delay: bool = True) -> RawResponse:
    """
    Fetch a single URL and return the raw response. No retries, no
    fallback to a browser — if this isn't enough for a given provider,
    that's a decision to make explicitly, not silently.
    """
    if respect_delay:
        time.sleep(settings.request_delay_seconds)

    log.info("Fetching %s", url)
    headers = {"User-Agent": settings.user_agent}
    with httpx.Client(headers=headers, follow_redirects=True, timeout=30) as client:
        response = client.get(url)

    log.info("Got %s (%d bytes) from %s", response.status_code, len(response.text), url)
    return RawResponse(
        url=url,
        status_code=response.status_code,
        text=response.text,
        fetched_at=time.time(),
    )
