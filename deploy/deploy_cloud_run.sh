#!/usr/bin/env bash
# =============================================================================
# APEX Autopilot — Google Cloud Run deploy (secret-safe, idempotent)
# -----------------------------------------------------------------------------
# Pushes sensitive values from the LOCAL .env into Secret Manager (never echoed,
# never committed), builds the container with Cloud Build, and deploys to
# Cloud Run with secrets mounted as env vars.
#
# Usage:
#   ./deploy/deploy_cloud_run.sh            # full: enable APIs, secrets, build, deploy
#   SKIP_SECRETS=1 ./deploy/deploy_cloud_run.sh   # redeploy code only
#
# Requirements: gcloud authenticated, billing enabled, .env present locally.
# =============================================================================
set -euo pipefail

PROJECT_ID="${PROJECT_ID:-$(gcloud config get-value project 2>/dev/null)}"
REGION="${REGION:-us-central1}"
SERVICE="${SERVICE:-apex-autopilot}"
REPO="${REPO:-apex}"                       # Artifact Registry repo
IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO}/${SERVICE}:$(date +%Y%m%d-%H%M%S)"
ENV_FILE="${ENV_FILE:-.env}"

if [[ -z "${PROJECT_ID}" || "${PROJECT_ID}" == "(unset)" ]]; then
  echo "ERROR: no GCP project set. Run: gcloud config set project <id>" >&2
  exit 1
fi
echo ">> Project=${PROJECT_ID} Region=${REGION} Service=${SERVICE}"

# --- Secrets we move into Secret Manager (sensitive only) --------------------
SECRET_KEYS=(
  GEMINI_API_KEY APEX_AUTH_SECRET APEX_SECRETS_KEY
  ALPACA_API_KEY ALPACA_SECRET_KEY
  KALSHI_API_KEY KALSHI_API_PRIVATE_KEY
  POLYGON_API_KEY SEC_API_KEY BRIGHTDATA_API_KEY TRADIER_SANDBOX_TOKEN
)

# --- Non-secret runtime config (safe to pass as plain env vars) --------------
PLAIN_ENV="AUTH_ENABLED=true,COOKIE_SECURE=true,COOKIE_SAMESITE=lax,\
ALLOW_OPEN_REGISTRATION=false,AUTH_RATE_LIMIT_PER_MIN=10,API_RATE_LIMIT_PER_MIN=120,\
GEMINI_MODEL=gemini-1.5-flash,LOG_LEVEL=INFO,APEX_ARB_SCAN_LOOP=false,\
PYTHONPATH=/app/src:/app/autopilot-local/backend:/app"

# 1) Enable required APIs -----------------------------------------------------
echo ">> Enabling APIs (run, cloudbuild, artifactregistry, secretmanager)..."
gcloud services enable \
  run.googleapis.com cloudbuild.googleapis.com \
  artifactregistry.googleapis.com secretmanager.googleapis.com \
  --project "${PROJECT_ID}"

# 2) Artifact Registry repo (idempotent) --------------------------------------
gcloud artifacts repositories describe "${REPO}" --location "${REGION}" \
  --project "${PROJECT_ID}" >/dev/null 2>&1 || \
gcloud artifacts repositories create "${REPO}" --repository-format=docker \
  --location "${REGION}" --description "APEX images" --project "${PROJECT_ID}"

# 3) Push secrets from local .env into Secret Manager -------------------------
# Reads each key's RAW value from .env (handles multiline RSA via python parser)
# and writes a new secret version. Values are NEVER printed.
SECRET_FLAGS=""
if [[ "${SKIP_SECRETS:-0}" != "1" ]]; then
  [[ -f "${ENV_FILE}" ]] || { echo "ERROR: ${ENV_FILE} not found" >&2; exit 1; }
  for KEY in "${SECRET_KEYS[@]}"; do
    VALUE="$(python3 deploy/_read_env_value.py "${ENV_FILE}" "${KEY}" || true)"
    if [[ -z "${VALUE}" ]]; then
      echo "   - ${KEY}: (absent in ${ENV_FILE}, skipping)"
      continue
    fi
    if ! gcloud secrets describe "${KEY}" --project "${PROJECT_ID}" >/dev/null 2>&1; then
      gcloud secrets create "${KEY}" --replication-policy=automatic --project "${PROJECT_ID}" >/dev/null
    fi
    printf '%s' "${VALUE}" | gcloud secrets versions add "${KEY}" --data-file=- --project "${PROJECT_ID}" >/dev/null
    echo "   - ${KEY}: new version stored"
    SECRET_FLAGS="${SECRET_FLAGS}${SECRET_FLAGS:+,}${KEY}=${KEY}:latest"
  done
else
  for KEY in "${SECRET_KEYS[@]}"; do
    gcloud secrets describe "${KEY}" --project "${PROJECT_ID}" >/dev/null 2>&1 && \
      SECRET_FLAGS="${SECRET_FLAGS}${SECRET_FLAGS:+,}${KEY}=${KEY}:latest"
  done
fi

# 4) Grant Cloud Run runtime SA access to the secrets -------------------------
PROJ_NUM="$(gcloud projects describe "${PROJECT_ID}" --format='value(projectNumber)')"
RUNTIME_SA="${PROJ_NUM}-compute@developer.gserviceaccount.com"
for KEY in "${SECRET_KEYS[@]}"; do
  gcloud secrets describe "${KEY}" --project "${PROJECT_ID}" >/dev/null 2>&1 || continue
  gcloud secrets add-iam-policy-binding "${KEY}" \
    --member="serviceAccount:${RUNTIME_SA}" \
    --role="roles/secretmanager.secretAccessor" \
    --project "${PROJECT_ID}" >/dev/null 2>&1 || true
done

# 5) Build image with Cloud Build --------------------------------------------
# IMPORTANT: use the pinned cloudbuild.yaml so it builds Dockerfile.cloudrun and
# NOT the dev-only ./Dockerfile (which runs `tail -f /dev/null`).
echo ">> Building image: ${IMAGE}"
gcloud builds submit --config cloudbuild.yaml \
  --substitutions="_IMAGE=${IMAGE}" --project "${PROJECT_ID}" .

# 6) Deploy to Cloud Run ------------------------------------------------------
echo ">> Deploying to Cloud Run..."
gcloud run deploy "${SERVICE}" \
  --image "${IMAGE}" \
  --region "${REGION}" \
  --project "${PROJECT_ID}" \
  --platform managed \
  --allow-unauthenticated \
  --port 8080 \
  --cpu 2 --memory 2Gi \
  --min-instances 1 --max-instances 4 \
  --timeout 300 \
  --set-env-vars "${PLAIN_ENV}" \
  ${SECRET_FLAGS:+--set-secrets "${SECRET_FLAGS}"}

URL="$(gcloud run services describe "${SERVICE}" --region "${REGION}" \
  --project "${PROJECT_ID}" --format='value(status.url)')"
echo ">> Deployed: ${URL}"
echo ">> Verifying /health ..."
curl -fsS "${URL}/health" && echo "  OK" || echo "  WARN: health check failed (check logs)"
