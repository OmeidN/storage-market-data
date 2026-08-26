"""
Playwright collector used only when plain HTTP is blocked (Cloudflare).

Not a stealth/CAPTCHA bypass. A real Chromium session is the planning.md
fallback when server-rendered HTML is unreachable via httpx.
"""
from __future__ import annotations

import time

from app.collectors.http import RawResponse
from app.config import settings
from app.logging import get_logger

log = get_logger(__name__)


def fetch_with_browser(url: str, *, respect_delay: bool = True) -> RawResponse:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise RuntimeError(
            "HTTP was blocked and Playwright is not installed. "
            "Install optional extra [browser] to collect ReadySpaces."
        ) from exc

    if respect_delay:
        time.sleep(settings.request_delay_seconds)

    log.info("Fetching %s with Playwright", url)
    fetched_at = time.time()
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            page = browser.new_page()
            response = page.goto(url, wait_until="domcontentloaded", timeout=45_000)
            status = response.status if response is not None else 0
            text = page.content()
        finally:
            browser.close()

    log.info("Playwright got %s (%d bytes) from %s", status, len(text), url)
    return RawResponse(url=url, status_code=status, text=text, fetched_at=fetched_at)
