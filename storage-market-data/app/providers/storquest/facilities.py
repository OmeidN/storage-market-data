"""Hand-picked StorQuest facility pages. Not a discovery crawler."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FacilityTarget:
    slug: str
    url: str


STORQUEST_FACILITIES: tuple[FacilityTarget, ...] = (
    FacilityTarget(
        slug="tracy-ca-225-gandy-dancer-drive",
        url="https://www.storquest.com/self-storage/ca/tracy/225-gandy-dancer-drive",
    ),
    FacilityTarget(
        slug="anaheim-ca-1431-s-sunkist-street",
        url="https://www.storquest.com/self-storage/ca/anaheim/1431-s-sunkist-street",
    ),
    FacilityTarget(
        slug="arlington-tx-1830-east-division-street",
        url="https://www.storquest.com/self-storage/tx/arlington/1830-east-division-street",
    ),
    FacilityTarget(
        slug="bedford-hills-ny-415-adams-street",
        url="https://www.storquest.com/self-storage/ny/bedford-hills/415-adams-street",
    ),
    FacilityTarget(
        slug="apopka-fl-2371-south-orange-blossom-trail",
        url="https://www.storquest.com/self-storage/fl/apopka/2371-south-orange-blossom-trail",
    ),
    FacilityTarget(
        slug="apache-junction-az-10461-east-apache-trail",
        url="https://www.storquest.com/self-storage/az/apache-junction/10461-east-apache-trail",
    ),
    FacilityTarget(
        slug="arvada-co-8495-n-interstate-70-frontage-road",
        url="https://www.storquest.com/self-storage/co/arvada/8495-n-interstate-70-frontage-road",
    ),
    FacilityTarget(
        slug="reno-nv-10815-double-r-boulevard",
        url="https://www.storquest.com/self-storage/nv/reno/10815-double-r-boulevard",
    ),
    FacilityTarget(
        slug="bellingham-wa-1155-lincoln-street",
        url="https://www.storquest.com/self-storage/wa/bellingham/1155-lincoln-street",
    ),
    FacilityTarget(
        slug="happy-valley-or-16576-se-sunnyside-road",
        url="https://www.storquest.com/self-storage/or/happy-valley/16576-se-sunnyside-road",
    ),
)
