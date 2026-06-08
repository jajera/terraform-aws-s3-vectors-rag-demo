#!/usr/bin/env bash
# Debug: generate Bedrock embeddings for local corpus files (not required for normal workflow).
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CORPUS_DIR="${1:-${ROOT_DIR}/docs/corpus}"

# shellcheck disable=SC1091
source "${ROOT_DIR}/scripts/export-env.sh"

EMBEDDING_MODEL_ID="${EMBEDDING_MODEL_ID}"
AWS_REGION="${AWS_REGION}"

"${ROOT_DIR}/scripts/check-bedrock-access.sh"

shopt -s nullglob
files=("${CORPUS_DIR}"/*.txt)
if ((${#files[@]} == 0)); then
  echo "No .txt files found in ${CORPUS_DIR}" >&2
  exit 1
fi

for f in "${files[@]}"; do
  base=$(basename "$f")
  req="/tmp/bedrock-req-${base}.json"
  out="/tmp/embedding-${base}.json"

  PYTHONPATH="${ROOT_DIR}" python3 - "${f}" "${req}" <<'PY'
import json
import sys
from pathlib import Path

from rag.fetch import document_body

body = document_body(Path(sys.argv[1]).read_text(encoding="utf-8"))
json.dump({"inputText": body}, open(sys.argv[2], "w", encoding="utf-8"))
PY

  aws bedrock-runtime invoke-model \
    --model-id "${EMBEDDING_MODEL_ID}" \
    --region "${AWS_REGION}" \
    --content-type application/json \
    --body "fileb://${req}" \
    "${out}"

  echo "Embedded ${base}"
done
