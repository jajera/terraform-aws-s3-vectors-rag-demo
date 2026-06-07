"""Lambda handler for automated AWS news corpus ingestion."""

from __future__ import annotations

import json
import logging
import os
import sys

# Lambda package layout: rag/ is copied alongside handler.py in the zip.
sys.path.insert(0, os.path.dirname(__file__))

from rag.config import Config
from rag.ingest import ingest_articles

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def _config_from_env() -> Config:
    # AWS_REGION is reserved on Lambda but set automatically by the runtime.
    region = os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION")
    if not region:
        raise RuntimeError("AWS_REGION is not available in the Lambda runtime")
    return Config(
        aws_region=region,
        source_bucket=os.environ["SOURCE_BUCKET"],
        vector_bucket=os.environ["VECTOR_BUCKET"],
        vector_index=os.environ["VECTOR_INDEX"],
        embedding_model_id=os.environ["EMBEDDING_MODEL_ID"],
        llm_model_id=os.environ["LLM_MODEL_ID"],
    )


def handler(event, context):
    source = "unknown"
    if isinstance(event, dict):
        source = event.get("source", source)

    logger.info("Starting ingest (source=%s)", source)
    result = ingest_articles(_config_from_env())
    logger.info("Ingest complete: %s", result)
    return {
        "statusCode": 200,
        "body": json.dumps(result),
    }
