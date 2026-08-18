"""
Fetch StorQuest facility pages, validate, store observations, and print JSON.

Usage:
    python scripts/scrape_facility.py
    python scripts/scrape_facility.py --limit 1
"""
import argparse
import json

from app.pipeline import scrape_all
from app.providers.storquest.facilities import STORQUEST_FACILITIES


def main() -> None:
    parser = argparse.ArgumentParser(description="Scrape StorQuest facility pages.")
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        metavar="N",
        help="Scrape only the first N facilities (default: all).",
    )
    args = parser.parse_args()
    targets = list(STORQUEST_FACILITIES)
    if args.limit is not None:
        targets = targets[: args.limit]

    outcomes = scrape_all(targets)
    failures = 0
    for outcome in outcomes:
        slug = outcome.target.slug
        if outcome.error is not None:
            failures += 1
            print(f"FAILED {slug}: {outcome.error}")
            continue
        page = outcome.page
        assert page is not None
        print(json.dumps(page.model_dump(mode="json"), indent=2))
        print(
            f"{slug}: parse_status={page.parse_status} "
            f"strategy={page.parse_strategy} units={len(page.units)}"
        )

    print(
        f"\nDone: {len(outcomes) - failures}/{len(outcomes)} succeeded, "
        f"{failures} failed (run continued through errors)."
    )


if __name__ == "__main__":
    main()
