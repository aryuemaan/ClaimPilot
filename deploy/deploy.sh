#!/usr/bin/env bash
# Deploy ClaimPilot to Cloud Run with Firestore + Cloud Storage.
#
#   export PROJECT_ID=my-gcp-project
#   export GOOGLE_API_KEY=...            # optional: AI Studio key (enables Gemma too)
#   ./deploy/deploy.sh
#
# Without GOOGLE_API_KEY the service uses Vertex AI through its own service account.
set -euo pipefail

PROJECT_ID="${PROJECT_ID:-$(gcloud config get-value project 2>/dev/null)}"
REGION="${REGION:-asia-south1}"
SERVICE="${SERVICE:-claimpilot}"
BUCKET="${BUCKET:-${PROJECT_ID}-claimpilot-files}"
GEMINI_MODEL="${GEMINI_MODEL:-gemini-3.8-flash}"
ADJUDICATOR_MODEL="${ADJUDICATOR_MODEL:-$GEMINI_MODEL}"
MIN_INSTANCES="${MIN_INSTANCES:-1}"
SA_NAME="claimpilot-run"
SA="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

if [[ -z "$PROJECT_ID" ]]; then
  echo "Set PROJECT_ID (or run: gcloud config set project <id>)" >&2
  exit 1
fi
cd "$(dirname "$0")/.."
gcloud config set project "$PROJECT_ID" >/dev/null

echo "==> Enabling APIs (first run takes a minute)"
gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com \
  firestore.googleapis.com storage.googleapis.com aiplatform.googleapis.com secretmanager.googleapis.com

echo "==> Firestore (native mode)"
if ! gcloud firestore databases describe --database="(default)" >/dev/null 2>&1; then
  gcloud firestore databases create --database="(default)" --location="$REGION" --type=firestore-native
fi

echo "==> Cloud Storage bucket gs://$BUCKET"
if ! gcloud storage buckets describe "gs://$BUCKET" >/dev/null 2>&1; then
  gcloud storage buckets create "gs://$BUCKET" --location="$REGION" --uniform-bucket-level-access
fi

echo "==> Service account $SA"
if ! gcloud iam service-accounts describe "$SA" >/dev/null 2>&1; then
  gcloud iam service-accounts create "$SA_NAME" --display-name="ClaimPilot on Cloud Run"
  sleep 5
fi
for ROLE in roles/datastore.user roles/aiplatform.user roles/logging.logWriter; do
  gcloud projects add-iam-policy-binding "$PROJECT_ID" --member="serviceAccount:$SA" --role="$ROLE" --condition=None >/dev/null
done
gcloud storage buckets add-iam-policy-binding "gs://$BUCKET" --member="serviceAccount:$SA" --role=roles/storage.objectAdmin >/dev/null

ENV_VARS="STORE_BACKEND=firestore,GCS_BUCKET=${BUCKET},GOOGLE_CLOUD_PROJECT=${PROJECT_ID},GEMINI_MODEL=${GEMINI_MODEL},ADJUDICATOR_MODEL=${ADJUDICATOR_MODEL},TZ=IST-5:30"
SECRET_ARGS=()
if [[ -n "${GOOGLE_API_KEY:-}" ]]; then
  echo "==> Storing the Gemini API key in Secret Manager"
  if gcloud secrets describe gemini-api-key >/dev/null 2>&1; then
    printf "%s" "$GOOGLE_API_KEY" | gcloud secrets versions add gemini-api-key --data-file=- >/dev/null
  else
    printf "%s" "$GOOGLE_API_KEY" | gcloud secrets create gemini-api-key --data-file=- --replication-policy=automatic >/dev/null
  fi
  gcloud secrets add-iam-policy-binding gemini-api-key --member="serviceAccount:$SA" --role=roles/secretmanager.secretAccessor >/dev/null
  SECRET_ARGS=(--set-secrets=GOOGLE_API_KEY=gemini-api-key:latest)
else
  echo "==> No GOOGLE_API_KEY set: using Vertex AI with the service account"
  ENV_VARS="${ENV_VARS},GOOGLE_GENAI_USE_ENTERPRISE=true,GOOGLE_CLOUD_LOCATION=${GOOGLE_CLOUD_LOCATION:-global}"
fi

echo "==> Building and deploying (Cloud Build, ~4-6 minutes)"
gcloud run deploy "$SERVICE" \
  --source . \
  --region "$REGION" \
  --service-account "$SA" \
  --allow-unauthenticated \
  --memory 1Gi --cpu 1 \
  --min-instances "$MIN_INSTANCES" --max-instances 3 \
  --no-cpu-throttling \
  --timeout 900 \
  --set-env-vars "$ENV_VARS" \
  ${SECRET_ARGS[@]+"${SECRET_ARGS[@]}"}

URL=$(gcloud run services describe "$SERVICE" --region "$REGION" --format='value(status.url)')
echo
echo "ClaimPilot is live:"
echo "  Landing page      $URL"
echo "  Customer app      $URL/claim"
echo "  Claims console    $URL/console"
echo "  Health check      $URL/api/health"
