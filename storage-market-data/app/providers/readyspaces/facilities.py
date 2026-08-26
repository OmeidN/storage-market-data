"""Hand-picked ReadySpaces facility pages. Not a discovery crawler."""
from __future__ import annotations

from app.providers.targets import FacilityTarget

READYSPACES_FACILITIES: tuple[FacilityTarget, ...] = (
    FacilityTarget(
        slug="los-angeles-downtown-los-angeles",
        url="https://readyspaces.com/location/los-angeles/downtown-los-angeles/",
        provider="readyspaces",
    ),
    FacilityTarget(
        slug="seattle-redmond",
        url="https://readyspaces.com/location/seattle/redmond/",
        provider="readyspaces",
    ),
    FacilityTarget(
        slug="los-angeles-south-gate",
        url="https://readyspaces.com/location/los-angeles/south-gate/",
        provider="readyspaces",
    ),
)
