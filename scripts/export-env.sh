#!/usr/bin/env bash
# Export Terraform outputs for local Streamlit debug only (not used by cloud UI).
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if ! terraform -chdir="${ROOT_DIR}" output -json >/dev/null 2>&1; then
  echo "terraform output failed — run terraform apply first" >&2
  return 1 2>/dev/null || exit 1
fi

exports="$(terraform -chdir="${ROOT_DIR}" output -json | jq -r '
  "export AWS_REGION=\(.aws_region.value | @sh)",
  "export SOURCE_BUCKET=\(.source_bucket_name.value | @sh)",
  "export VECTOR_BUCKET=\(.vector_bucket_name.value | @sh)",
  "export VECTOR_INDEX=\(.vector_index_name.value | @sh)",
  "export EMBEDDING_MODEL_ID=\(.embedding_model_id.value | @sh)",
  "export LLM_MODEL_ID=\(.llm_model_id.value | @sh)",
  "export INGEST_FUNCTION_NAME=\(.ingest_function_name.value | @sh)"
')"

eval "${exports}"

echo "Exported RAG environment variables for local debug."
