"""
Day-one entry point: fetch one facility page, save the raw response, parse
it, and print the result. This is the whole pipeline for Milestone 1 —
resist the urge to add a database, args for multiple facilities, or a
provider registry here. That's later phases.

Usage:
    python scripts/scrape_facility.py
"""
import json

from app.collectors.http import fetch
from app.providers.storquest.parser import parse_facility_page
from app.raw_storage import save_raw

FACILITY_URL = "https://www.storquest.com/self-storage/ca/tracy/225-gandy-dancer-drive"
FACILITY_SLUG = "tracy-ca-225-gandy-dancer-drive"


def main() -> None:
    response = fetch(FACILITY_URL)

    if response.status_code != 200:
        print(f"Non-200 response ({response.status_code}) — not parsing. "
              f"Saving raw response for inspection regardless.")

    raw_path = save_raw(response, provider="storquest", facility_slug=FACILITY_SLUG)
    print(f"Saved raw response to {raw_path}")

    if response.status_code != 200:
        return

    result = parse_facility_page(response.text)
    print(json.dumps(result, indent=2))
    print(f"\nParse strategy used: {result['parse_strategy']}")
    print(f"Units found: {len(result['units']) if result['units'] else 0}")


if __name__ == "__main__":
    main()
