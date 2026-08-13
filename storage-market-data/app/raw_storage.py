"""
Saves raw responses to disk so the parser can be developed and re-run
against a saved copy instead of re-hitting the live site every time.
This is Phase 5 in planning.md, kept intentionally tiny — a real
raw-storage/retention policy is a later-phase concern.
"""
from __future__ import annotations

import datetime as dt
import re
from pathlib import Path

from app.collectors.http import RawResponse
from app.config import settings


def _slugify(text: str) -> str:
    text = text.strip().lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")


def save_raw(response: RawResponse, *, provider: str, facility_slug: str) -> Path:
    settings.raw_data_dir.mkdir(parents=True, exist_ok=True)
    timestamp = dt.datetime.fromtimestamp(response.fetched_at, tz=dt.timezone.utc)
    filename = f"{provider}__{_slugify(facility_slug)}__{timestamp:%Y%m%dT%H%M%SZ}.html"
    path = settings.raw_data_dir / filename
    path.write_text(response.text, encoding="utf-8")
    return path
