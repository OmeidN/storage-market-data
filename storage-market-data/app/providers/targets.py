"""Shared scrape target. Provider-specific lists live under providers/<name>/."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FacilityTarget:
    slug: str
    url: str
    provider: str = "storquest"
