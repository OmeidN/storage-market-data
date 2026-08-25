#!/usr/bin/env bash
# Truncate-reload Postgres -> BigQuery raw, then dbt seed+run marts.
set -euo pipefail
python scripts/replicate_to_bigquery.py
cd warehouse
dbt seed --select facility_market_map --target prod --profiles-dir .
dbt run --target prod --profiles-dir .
