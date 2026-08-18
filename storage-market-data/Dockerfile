FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml README.md ./
COPY app ./app
COPY scripts ./scripts
COPY alembic.ini ./
COPY alembic ./alembic

RUN pip install --no-cache-dir .

ENV PYTHONUNBUFFERED=1
ENV RAW_DATA_DIR=/app/data/raw

CMD ["python", "scripts/scrape_facility.py"]
