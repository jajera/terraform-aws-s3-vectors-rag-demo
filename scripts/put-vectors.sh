#!/usr/bin/env bash
# Debug: upload local embeddings to S3 Vectors (not required for normal workflow).
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CORPUS_DIR="${1:-${ROOT_DIR}/docs/corpus}"
VECTORS_FILE="${2:-/tmp/vectors.json}"

# shellcheck disable=SC1091
source "${ROOT_DIR}/scripts/export-env.sh"

PYTHONPATH="${ROOT_DIR}" python3 - "${CORPUS_DIR}" "${VECTORS_FILE}" <<'PY'
import json
import sys
from pathlib import Path

from rag.fetch import parse_document_headers

corpus_dir = Path(sys.argv[1])
vectors_file = Path(sys.argv[2])
vectors = []

for path in sorted(corpus_dir.glob("*.txt")):
    base = path.name
    slug = path.stem
    embedding_file = Path(f"/tmp/embedding-{base}.json")
    if not embedding_file.exists():
        raise SystemExit(f"Missing embedding file: {embedding_file}")

    text = path.read_text(encoding="utf-8")
    headers = parse_document_headers(text)
    url = headers.get("url", "")
    url_hash = slug.rsplit("-", 1)[-1] if "-" in slug else slug[:8]
    key = f"article-{url_hash}-chunk-000"

    embedding = json.loads(embedding_file.read_text())["embedding"]
    vectors.append(
        {
            "key": key,
            "data": {"float32": embedding},
            "metadata": {
                "source": base,
                "title": headers.get("title", base),
                "url": url,
                "published": headers.get("published", ""),
                "feed": headers.get("feed", ""),
                "chunk": "0",
            },
        }
    )

vectors_file.write_text(json.dumps(vectors))
print(f"Built {len(vectors)} vectors in {vectors_file}")
PY

aws s3vectors put-vectors \
  --region "${AWS_REGION}" \
  --vector-bucket-name "${VECTOR_BUCKET}" \
  --index-name "${VECTOR_INDEX}" \
  --vectors "file://${VECTORS_FILE}"

echo "Done."
