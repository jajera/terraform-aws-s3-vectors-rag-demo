#!/usr/bin/env bash
# Download AWS news RSS corpus into docs/corpus/ (debug / local inspection only).
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CORPUS_DIR="${ROOT_DIR}/docs/corpus"

mkdir -p "${CORPUS_DIR}"
PYTHONPATH="${ROOT_DIR}" python3 -m rag.fetch --write "${CORPUS_DIR}"
