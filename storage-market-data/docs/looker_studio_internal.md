# Looker Studio — internal exploration only

This is **not** the client deliverable (that is Milestone 7). Use it to
inspect dbt marts. Velocity numbers that are still gated must show as
insufficient history / blank, never as a fake average.

See `docs/velocity_definitions.md` rule 4.

## Data

GCP project: `storagemarketdata`  
Region: `us-west1`

| Mart | BigQuery table |
|---|---|
| Rental velocity | `storage_market_data_marts.rental_velocity_by_facility` |
| Price history | `storage_market_data_marts.price_history_by_market` |
| Competitive position | `storage_market_data_marts.facility_competitive_positioning` |

Console: [BigQuery marts](https://console.cloud.google.com/bigquery?project=storagemarketdata)

Open Looker Studio: [Create report](https://lookerstudio.google.com/navigation/reporting)

1. Create → Data source → **BigQuery**.
2. My projects → `storagemarketdata` → `storage_market_data_marts` → `rental_velocity_by_facility`.
3. Add `facility_competitive_positioning` as a second data source if you want side-by-side asking price.
4. Table chart: rows = `slug`, columns include `confidence`, `snapshot_dates`, `lease_event_count`, `avg_days_to_lease`, `insufficient_history`.
5. Filter or conditional formatting: `insufficient_history = true` should be obvious (all 10 facilities until history exists).

Do not publish this report outside the project.
