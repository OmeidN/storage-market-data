"""
Copy facilities, units, observations from Postgres into BigQuery.

Faithful truncate-and-reload (no transforms). See docs/velocity_definitions.md.
Usage:
    python scripts/replicate_to_bigquery.py
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone

from google.cloud import bigquery
from sqlalchemy import text

from app.database.engine import get_engine

PROJECT = os.getenv("GCP_PROJECT", "storagemarketdata")
DATASET = os.getenv("BQ_RAW_DATASET", "storage_market_data_raw")
LOCATION = os.getenv("BQ_LOCATION", "us-west1")

TABLES = (
    "facilities",
    "units",
    "observations",
)

SCHEMAS: dict[str, list[bigquery.SchemaField]] = {
    "facilities": [
        bigquery.SchemaField("id", "INTEGER", mode="REQUIRED"),
        bigquery.SchemaField("provider", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("slug", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("url", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("name", "STRING"),
        bigquery.SchemaField("address", "STRING"),
        bigquery.SchemaField("created_at", "TIMESTAMP", mode="REQUIRED"),
    ],
    "units": [
        bigquery.SchemaField("id", "INTEGER", mode="REQUIRED"),
        bigquery.SchemaField("facility_id", "INTEGER", mode="REQUIRED"),
        bigquery.SchemaField("identity_key", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("provider_unit_id", "STRING"),
        bigquery.SchemaField("width_ft", "INTEGER", mode="REQUIRED"),
        bigquery.SchemaField("length_ft", "INTEGER", mode="REQUIRED"),
        bigquery.SchemaField("features", "STRING"),
    ],
    "observations": [
        bigquery.SchemaField("id", "INTEGER", mode="REQUIRED"),
        bigquery.SchemaField("unit_id", "INTEGER", mode="REQUIRED"),
        bigquery.SchemaField("scraped_at", "TIMESTAMP", mode="REQUIRED"),
        bigquery.SchemaField("standard_price", "INTEGER"),
        bigquery.SchemaField("promo_price", "INTEGER"),
        bigquery.SchemaField("availability_status", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("availability_text", "STRING"),
        bigquery.SchemaField("free_first_month", "BOOLEAN", mode="REQUIRED"),
        bigquery.SchemaField("parse_strategy", "STRING"),
    ],
}


def _json_safe(value: object) -> object:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.isoformat()
    if isinstance(value, (list, dict)):
        return json.dumps(value)
    return value


def fetch_rows(table: str) -> list[dict]:
    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute(text(f"SELECT * FROM {table} ORDER BY id"))
        rows = []
        for mapping in result.mappings():
            rows.append({k: _json_safe(v) for k, v in dict(mapping).items()})
        return rows


def ensure_dataset(client: bigquery.Client) -> None:
    dataset_id = f"{PROJECT}.{DATASET}"
    try:
        client.get_dataset(dataset_id)
    except Exception:
        dataset = bigquery.Dataset(dataset_id)
        dataset.location = LOCATION
        client.create_dataset(dataset, exists_ok=True)


def load_table(client: bigquery.Client, table: str, rows: list[dict]) -> int:
    table_id = f"{PROJECT}.{DATASET}.{table}"
    job_config = bigquery.LoadJobConfig(
        schema=SCHEMAS[table],
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
        source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
    )
    # Empty reload still truncates so a second run cannot duplicate rows.
    job = client.load_table_from_json(rows, table_id, job_config=job_config)
    job.result()
    dest = client.get_table(table_id)
    return dest.num_rows


def main() -> None:
    client = bigquery.Client(project=PROJECT, location=LOCATION)
    ensure_dataset(client)
    print(f"Replicating Postgres -> {PROJECT}.{DATASET} ({LOCATION})")
    for table in TABLES:
        rows = fetch_rows(table)
        bq_count = load_table(client, table, rows)
        print(f"  {table}: postgres={len(rows)} bigquery={bq_count}")
        if bq_count != len(rows):
            raise SystemExit(f"row count mismatch for {table}")
    print("Replication ok")


if __name__ == "__main__":
    main()
