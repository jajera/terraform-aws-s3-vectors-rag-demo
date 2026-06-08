"""Environment-based configuration for the RAG pipeline."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    aws_region: str
    source_bucket: str
    vector_bucket: str
    vector_index: str
    embedding_model_id: str
    llm_model_id: str
    ingest_function_name: str | None = None

    @property
    def documents_prefix(self) -> str:
        return "documents/"

    @property
    def last_ingest_key(self) -> str:
        return f"{self.documents_prefix}.last-ingest"


def load_config() -> Config:
    """Load required settings from environment variables."""

    def require(name: str) -> str:
        value = os.environ.get(name, "").strip()
        if not value:
            raise RuntimeError(f"Missing required environment variable: {name}")
        return value

    ingest_name = os.environ.get("INGEST_FUNCTION_NAME", "").strip() or None

    return Config(
        aws_region=require("AWS_REGION"),
        source_bucket=require("SOURCE_BUCKET"),
        vector_bucket=require("VECTOR_BUCKET"),
        vector_index=require("VECTOR_INDEX"),
        embedding_model_id=require("EMBEDDING_MODEL_ID"),
        llm_model_id=require("LLM_MODEL_ID"),
        ingest_function_name=ingest_name,
    )
