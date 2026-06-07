#!/usr/bin/env bash
# Verify Bedrock model access before running the RAG pipeline.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
AWS_REGION="$(terraform -chdir="${ROOT_DIR}" output -raw aws_region)"
EMBEDDING_MODEL_ID="$(terraform -chdir="${ROOT_DIR}" output -raw embedding_model_id)"
LLM_MODEL_ID="$(terraform -chdir="${ROOT_DIR}" output -raw llm_model_id)"

invoke_smoke_test() {
  local model_id="$1"
  local label="$2"
  local body_file="$3"
  local out_file err_file

  out_file="$(mktemp)"
  err_file="$(mktemp)"

  if aws bedrock-runtime invoke-model \
    --model-id "${model_id}" \
    --region "${AWS_REGION}" \
    --content-type application/json \
    --body "fileb://${body_file}" \
    "${out_file}" 2>"${err_file}"; then
    echo "OK  ${label}: ${model_id}"
    rm -f "${out_file}" "${err_file}"
    return 0
  fi

  echo "FAIL ${label}: ${model_id}" >&2
  sed 's/^/  /' "${err_file}" >&2
  rm -f "${out_file}" "${err_file}"
  return 1
}

print_remediation() {
  cat >&2 <<EOF

Bedrock invoke failed. Common causes:

  1. Operation not allowed — models are not enabled for this account/region, or an
     Organization SCP blocks bedrock:InvokeModel (you also hit SCP errors on S3).
  2. AccessDeniedException — the active IAM identity lacks bedrock:InvokeModel on
     the model ARN. Use an admin profile with Bedrock access.
  3. Anthropic models — submit the one-time use case form if not done for this org.

Remediation:
  - Run: export AWS_PROFILE=jgnscri-sandbox   # or your admin profile
  - Open Bedrock in ${AWS_REGION} and enable Titan Embeddings V2 + Claude Sonnet 4.5.
  - Ask your AWS Organization admin to allow bedrock:InvokeModel if admin still fails.
  - Re-apply Terraform after IAM changes if needed.

Docs: https://docs.aws.amazon.com/bedrock/latest/userguide/model-access.html
EOF
}

embed_req="$(mktemp)"
llm_req="$(mktemp)"
trap 'rm -f "${embed_req}" "${llm_req}"' EXIT

jq -n '{inputText: "bedrock access check"}' >"${embed_req}"
jq -n \
  '{
    anthropic_version: "bedrock-2023-05-31",
    max_tokens: 16,
    messages: [{role: "user", content: "Reply with OK"}]
  }' >"${llm_req}"

failed=0
invoke_smoke_test "${EMBEDDING_MODEL_ID}" "embedding model" "${embed_req}" || failed=1
invoke_smoke_test "${LLM_MODEL_ID}" "LLM" "${llm_req}" || failed=1

if ((failed)); then
  print_remediation
  exit 1
fi

echo "Bedrock access verified in ${AWS_REGION}."
