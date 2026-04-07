#!/usr/bin/env bash
set -euo pipefail

PROJECT_ID="${PROJECT_ID:-project-05a5d388-27e0-4fe6-aa5}"
REGION="${REGION:-us-central1}"
SERVICE="${SERVICE:-boq-auto-api}"
BUCKET="${BUCKET:-boq-auto-artifacts-project-05a5d388-27e0-4fe6-aa5}"
IMAGE="${IMAGE:-$REGION-docker.pkg.dev/$PROJECT_ID/boq-auto/boq-auto-api:latest}"
SERVICE_ACCOUNT="${SERVICE_ACCOUNT:-boq-auto-runtime@$PROJECT_ID.iam.gserviceaccount.com}"
CLOUD_SQL_CONNECTION_NAME="${CLOUD_SQL_CONNECTION_NAME:-$PROJECT_ID:us-central1:boq-auto-db}"
DB_NAME="${DB_NAME:-boq_auto}"
DB_USER="${DB_USER:-boq_auto_user}"
DB_PASSWORD_SECRET="${DB_PASSWORD_SECRET:-boq-auto-db-password}"
DEPLOY_FRONTEND="${DEPLOY_FRONTEND:-true}"
DEPLOY_BACKEND="${DEPLOY_BACKEND:-true}"
RUN_CHECKS="${RUN_CHECKS:-true}"

if ! command -v gcloud >/dev/null 2>&1; then
  echo "gcloud is required in Cloud Shell." >&2
  exit 1
fi

if ! command -v firebase >/dev/null 2>&1; then
  echo "firebase CLI is required in Cloud Shell." >&2
  exit 1
fi

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

echo "==> Pulling latest source"
git pull

echo "==> Deployment settings"
echo "PROJECT_ID=$PROJECT_ID"
echo "REGION=$REGION"
echo "SERVICE=$SERVICE"
echo "BUCKET=$BUCKET"
echo "IMAGE=$IMAGE"

if [[ "$DEPLOY_BACKEND" == "true" ]]; then
  echo "==> Building backend image"
  gcloud builds submit --tag "$IMAGE" .

  echo "==> Deploying backend to Cloud Run"
  gcloud run deploy "$SERVICE" \
    --image "$IMAGE" \
    --region "$REGION" \
    --platform managed \
    --allow-unauthenticated \
    --port 8080 \
    --service-account "$SERVICE_ACCOUNT" \
    --add-cloudsql-instances "$CLOUD_SQL_CONNECTION_NAME" \
    --set-env-vars "BOQ_AUTO_GCS_BUCKET=$BUCKET,BOQ_AUTO_API_DB_GCS_URI=gs://$BUCKET/runtime/qs_database.xlsx,BOQ_AUTO_CLOUD_SQL_CONNECTION_NAME=$CLOUD_SQL_CONNECTION_NAME,BOQ_AUTO_DB_NAME=$DB_NAME,BOQ_AUTO_DB_USER=$DB_USER,BOQ_AUTO_FIREBASE_AUTH_ENABLED=true,BOQ_AUTO_FIREBASE_PROJECT_ID=$PROJECT_ID" \
    --update-secrets "BOQ_AUTO_DB_PASSWORD=$DB_PASSWORD_SECRET:latest"
fi

if [[ "$DEPLOY_FRONTEND" == "true" ]]; then
  echo "==> Deploying frontend to Firebase App Hosting"
  firebase deploy --only apphosting
fi

if [[ "$RUN_CHECKS" == "true" ]]; then
  echo "==> Running quick backend checks"
  SERVICE_URL="$(gcloud run services describe "$SERVICE" --region "$REGION" --format='value(status.url)')"
  echo "Backend: $SERVICE_URL"
  curl "$SERVICE_URL/health"
  echo
  curl "$SERVICE_URL/jobs"
  echo
fi

echo "==> Deployment complete"
