#!/usr/bin/env bash
# =============================================================================
# APEX Autopilot — Google Cloud Run deploy (backend + frontend, 2 URLs)
# -----------------------------------------------------------------------------
# Deploys:
#   1. apex-autopilot       — FastAPI backend  (/health, /docs, /api/*)
#   2. apex-autopilot-web   — Next.js terminal (/, /dashboard/*)
#
# Usage:
#   ./deploy/deploy_cloud_run.sh
#   SKIP_SECRETS=1 ./deploy/deploy_cloud_run.sh
#   SKIP_FRONTEND=1 ./deploy/deploy_cloud_run.sh   # backend only
# =============================================================================
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

PROJECT_ID="${PROJECT_ID:-$(gcloud config get-value project 2>/dev/null)}"
REGION="${REGION:-us-central1}"
SERVICE_BACKEND="${SERVICE_BACKEND:-apex-autopilot}"
SERVICE_FRONTEND="${SERVICE_FRONTEND:-apex-autopilot-web}"
REPO="${REPO:-apex}"
TS="$(date +%Y%m%d-%H%M%S)"
IMAGE_BACKEND="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO}/${SERVICE_BACKEND}:${TS}"
IMAGE_FRONTEND="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO}/${SERVICE_FRONTEND}:${TS}"
ENV_FILE="${ENV_FILE:-.env}"

if [[ -z "${PROJECT_ID}" || "${PROJECT_ID}" == "(unset)" ]]; then
  echo "ERROR: no GCP project set. Run: gcloud config set project <id>" >&2
  exit 1
fi
echo ">> Project=${PROJECT_ID} Region=${REGION}"
echo ">> Backend service=${SERVICE_BACKEND}  Frontend service=${SERVICE_FRONTEND}"

SECRET_KEYS=(
  GEMINI_API_KEY APEX_AUTH_SECRET APEX_SECRETS_KEY
  ALPACA_API_KEY ALPACA_SECRET_KEY
  KALSHI_API_KEY KALSHI_API_PRIVATE_KEY
  POLYGON_API_KEY SEC_API_KEY BRIGHTDATA_API_KEY TRADIER_SANDBOX_TOKEN
)

PLAIN_ENV_BASE="AUTH_ENABLED=true,COOKIE_SECURE=true,COOKIE_SAMESITE=none,\
ALLOW_OPEN_REGISTRATION=false,AUTH_RATE_LIMIT_PER_MIN=10,API_RATE_LIMIT_PER_MIN=120,\
GEMINI_MODEL=gemini-1.5-flash,LOG_LEVEL=INFO,APEX_ARB_SCAN_LOOP=true,\
SHOWCASE_MODE=true,SHOWCASE_ARB_COUNT=100,SHOWCASE_PROPOSAL_COUNT=32,\
PYTHONPATH=/app/src:/app/autopilot-local/backend:/app"

echo ">> Enabling APIs..."
gcloud services enable \
  run.googleapis.com cloudbuild.googleapis.com \
  artifactregistry.googleapis.com secretmanager.googleapis.com \
  --project "${PROJECT_ID}"

gcloud artifacts repositories describe "${REPO}" --location "${REGION}" \
  --project "${PROJECT_ID}" >/dev/null 2>&1 || \
gcloud artifacts repositories create "${REPO}" --repository-format=docker \
  --location "${REGION}" --description "APEX images" --project "${PROJECT_ID}"

SECRET_FLAGS=""
if [[ "${SKIP_SECRETS:-0}" != "1" ]]; then
  [[ -f "${ENV_FILE}" ]] || { echo "ERROR: ${ENV_FILE} not found" >&2; exit 1; }
  for KEY in "${SECRET_KEYS[@]}"; do
    VALUE="$(python3 deploy/_read_env_value.py "${ENV_FILE}" "${KEY}" || true)"
    if [[ -z "${VALUE}" ]]; then
      echo "   - ${KEY}: (absent, skipping)"
      continue
    fi
    if ! gcloud secrets describe "${KEY}" --project "${PROJECT_ID}" >/dev/null 2>&1; then
      gcloud secrets create "${KEY}" --replication-policy=automatic --project "${PROJECT_ID}" >/dev/null
    fi
    printf '%s' "${VALUE}" | gcloud secrets versions add "${KEY}" --data-file=- --project "${PROJECT_ID}" >/dev/null
    echo "   - ${KEY}: stored"
    SECRET_FLAGS="${SECRET_FLAGS}${SECRET_FLAGS:+,}${KEY}=${KEY}:latest"
  done
else
  for KEY in "${SECRET_KEYS[@]}"; do
    gcloud secrets describe "${KEY}" --project "${PROJECT_ID}" >/dev/null 2>&1 && \
      SECRET_FLAGS="${SECRET_FLAGS}${SECRET_FLAGS:+,}${KEY}=${KEY}:latest"
  done
fi

PROJ_NUM="$(gcloud projects describe "${PROJECT_ID}" --format='value(projectNumber)')"
RUNTIME_SA="${PROJ_NUM}-compute@developer.gserviceaccount.com"
for KEY in "${SECRET_KEYS[@]}"; do
  gcloud secrets describe "${KEY}" --project "${PROJECT_ID}" >/dev/null 2>&1 || continue
  gcloud secrets add-iam-policy-binding "${KEY}" \
    --member="serviceAccount:${RUNTIME_SA}" \
    --role="roles/secretmanager.secretAccessor" \
    --project "${PROJECT_ID}" >/dev/null 2>&1 || true
done

# --- Backend -----------------------------------------------------------------
echo ">> Building backend: ${IMAGE_BACKEND}"
gcloud builds submit --config cloudbuild.yaml \
  --substitutions="_IMAGE=${IMAGE_BACKEND}" --project "${PROJECT_ID}" .

echo ">> Deploying backend..."
gcloud run deploy "${SERVICE_BACKEND}" \
  --image "${IMAGE_BACKEND}" \
  --region "${REGION}" \
  --project "${PROJECT_ID}" \
  --platform managed \
  --allow-unauthenticated \
  --port 8080 \
  --cpu 2 --memory 2Gi \
  --min-instances 1 --max-instances 4 \
  --timeout 300 \
  --set-env-vars "${PLAIN_ENV_BASE}" \
  ${SECRET_FLAGS:+--set-secrets "${SECRET_FLAGS}"}

BACKEND_URL="$(gcloud run services describe "${SERVICE_BACKEND}" --region "${REGION}" \
  --project "${PROJECT_ID}" --format='value(status.url)')"
BACKEND_URL="${BACKEND_URL%/}"
echo ">> Backend: ${BACKEND_URL}"
curl -fsS "${BACKEND_URL}/health" >/dev/null && echo "   /health OK" || echo "   WARN: /health failed"

FRONTEND_URL=""
if [[ "${SKIP_FRONTEND:-0}" != "1" ]]; then
  # --- Frontend --------------------------------------------------------------
  echo ">> Building frontend (proxy → ${BACKEND_URL}): ${IMAGE_FRONTEND}"
  gcloud builds submit --config cloudbuild.frontend.yaml \
    --ignore-file=deploy/gcloudignore.frontend \
    --substitutions="_IMAGE=${IMAGE_FRONTEND},_APEX_BACKEND_URL=${BACKEND_URL}" \
    --project "${PROJECT_ID}" .

  echo ">> Deploying frontend..."
  gcloud run deploy "${SERVICE_FRONTEND}" \
    --image "${IMAGE_FRONTEND}" \
    --region "${REGION}" \
    --project "${PROJECT_ID}" \
    --platform managed \
    --allow-unauthenticated \
    --port 8080 \
    --cpu 1 --memory 1Gi \
    --min-instances 0 --max-instances 4 \
    --timeout 300

  FRONTEND_URL="$(gcloud run services describe "${SERVICE_FRONTEND}" --region "${REGION}" \
    --project "${PROJECT_ID}" --format='value(status.url)')"
  FRONTEND_URL="${FRONTEND_URL%/}"
  echo ">> Frontend: ${FRONTEND_URL}"
  curl -fsS -o /dev/null -w "   GET / → %{http_code}\n" "${FRONTEND_URL}/" || true

  # Link backend CORS + root index to frontend URL
  CORS_ENV="CORS_ORIGINS=${FRONTEND_URL},PUBLIC_DEMO_URL=${FRONTEND_URL},FRONTEND_URL=${FRONTEND_URL}"
  echo ">> Updating backend CORS for frontend origin..."
  gcloud run services update "${SERVICE_BACKEND}" \
    --region "${REGION}" \
    --project "${PROJECT_ID}" \
    --update-env-vars "${CORS_ENV}"
fi

mkdir -p data
printf '%s\n' "${BACKEND_URL}" > data/cloud_run_url.txt
if [[ -n "${FRONTEND_URL}" ]]; then
  printf '%s\n' "${FRONTEND_URL}" > data/cloud_run_frontend_url.txt
fi
python3 - <<PY
import json
from pathlib import Path
payload = {
    "backend": "${BACKEND_URL}",
    "frontend": "${FRONTEND_URL}" or None,
}
Path("data/cloud_run_urls.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
print(json.dumps(payload, indent=2))
PY

echo ""
echo "=========================================="
echo "  Backend:  ${BACKEND_URL}"
echo "  Frontend: ${FRONTEND_URL:-skipped}"
echo "=========================================="
echo "  Terminal → ${FRONTEND_URL:-(deploy frontend)}/dashboard"
echo "  API docs → ${BACKEND_URL}/docs"
echo "  Health   → ${BACKEND_URL}/health"
