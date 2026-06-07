#!/usr/bin/env bash
# Build web/config.js and deploy static assets to Amplify Hosting.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUILD_DIR="${ROOT_DIR}/.build/web"
ZIP_FILE="${ROOT_DIR}/.build/web.zip"

: "${API_ENDPOINT:?API_ENDPOINT is required}"
: "${AWS_REGION:?AWS_REGION is required}"
: "${COGNITO_USER_POOL_ID:?COGNITO_USER_POOL_ID is required}"
: "${COGNITO_CLIENT_ID:?COGNITO_CLIENT_ID is required}"
: "${AMPLIFY_APP_ID:?AMPLIFY_APP_ID is required}"
: "${AMPLIFY_BRANCH:?AMPLIFY_BRANCH is required}"

API_URL="${API_ENDPOINT%/}"

rm -rf "${BUILD_DIR}" "${ZIP_FILE}"
mkdir -p "${BUILD_DIR}"

cp "${ROOT_DIR}/web/index.html" "${BUILD_DIR}/"
cp "${ROOT_DIR}/web/styles.css" "${BUILD_DIR}/"
cp "${ROOT_DIR}/web/auth.js" "${BUILD_DIR}/"
cp "${ROOT_DIR}/web/api.js" "${BUILD_DIR}/"
cp "${ROOT_DIR}/web/app.js" "${BUILD_DIR}/"

sed \
  -e "s|__API_URL__|${API_URL}|g" \
  -e "s|__AWS_REGION__|${AWS_REGION}|g" \
  -e "s|__COGNITO_USER_POOL_ID__|${COGNITO_USER_POOL_ID}|g" \
  -e "s|__COGNITO_CLIENT_ID__|${COGNITO_CLIENT_ID}|g" \
  "${ROOT_DIR}/web/config.template.js" >"${BUILD_DIR}/config.js"

(
  cd "${BUILD_DIR}"
  zip -qr "${ZIP_FILE}" .
)

DEPLOY_JSON="$(
  aws amplify create-deployment \
    --app-id "${AMPLIFY_APP_ID}" \
    --branch-name "${AMPLIFY_BRANCH}" \
    --region "${AWS_REGION}" \
    --output json
)"

JOB_ID="$(echo "${DEPLOY_JSON}" | jq -r '.jobId')"
ZIP_UPLOAD_URL="$(echo "${DEPLOY_JSON}" | jq -r '.zipUploadUrl')"

curl -fsS -T "${ZIP_FILE}" "${ZIP_UPLOAD_URL}"

aws amplify start-deployment \
  --app-id "${AMPLIFY_APP_ID}" \
  --branch-name "${AMPLIFY_BRANCH}" \
  --job-id "${JOB_ID}" \
  --region "${AWS_REGION}"

echo "Amplify deployment ${JOB_ID} started for app ${AMPLIFY_APP_ID}."
