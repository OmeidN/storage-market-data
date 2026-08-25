#!/usr/bin/env bash
# Build/push the warehouse replicate image. Does not replace app:latest.
set -euo pipefail

PROJECT="${GCP_PROJECT:-storagemarketdata}"
REGION="${GCP_REGION:-us-west1}"
REPO="${AR_REPO:-storage-market-data}"
IMAGE="${REGION}-docker.pkg.dev/${PROJECT}/${REPO}/replicate:latest"

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

gcloud auth configure-docker "${REGION}-docker.pkg.dev" --quiet
docker build -f warehouse/Dockerfile -t "$IMAGE" .
docker push "$IMAGE"
gcloud artifacts docker images list "${REGION}-docker.pkg.dev/${PROJECT}/${REPO}/replicate"
