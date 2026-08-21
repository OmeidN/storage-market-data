#!/usr/bin/env bash
# Build the existing Dockerfile and push to Artifact Registry.
# Usage (from storage-market-data/):
#   bash scripts/gcp_push_image.sh
set -euo pipefail

PROJECT="${GCP_PROJECT:-storagemarketdata}"
REGION="${GCP_REGION:-us-west1}"
REPO="${AR_REPO:-storage-market-data}"
IMAGE="${REGION}-docker.pkg.dev/${PROJECT}/${REPO}/app:latest"

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if ! gcloud artifacts repositories describe "$REPO" --location="$REGION" >/dev/null 2>&1; then
  gcloud artifacts repositories create "$REPO" \
    --repository-format=docker \
    --location="$REGION" \
    --description="storage-market-data app images"
fi

gcloud auth configure-docker "${REGION}-docker.pkg.dev" --quiet
docker build -t "$IMAGE" .
docker push "$IMAGE"
gcloud artifacts docker images list "${REGION}-docker.pkg.dev/${PROJECT}/${REPO}/app"
