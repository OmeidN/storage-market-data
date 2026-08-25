# Image for the replicate-to-bigquery Cloud Run Job only.
# Does not replace the scrape Dockerfile.
FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml README.md ./
COPY app ./app
COPY scripts/replicate_to_bigquery.py ./scripts/replicate_to_bigquery.py
COPY scripts/replicate_and_transform.sh ./scripts/replicate_and_transform.sh
COPY warehouse ./warehouse

RUN pip install --no-cache-dir . "google-cloud-bigquery>=3.27" "dbt-bigquery>=1.8,<2" \
    && chmod +x scripts/replicate_and_transform.sh

ENV PYTHONUNBUFFERED=1
ENV GCP_PROJECT=storagemarketdata
ENV BQ_RAW_DATASET=storage_market_data_raw
ENV BQ_LOCATION=us-west1
ENV DBT_PROFILES_DIR=/app/warehouse

CMD ["./scripts/replicate_and_transform.sh"]
