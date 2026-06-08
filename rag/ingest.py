"""Ingest AWS news articles into S3 and S3 Vectors."""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from typing import Any

import boto3
from botocore.exceptions import ClientError

from rag.config import Config
from rag.fetch import Article, document_body, fetch_articles, parse_document_headers


def _bedrock_embed(client: Any, model_id: str, text: str) -> list[float]:
    last_error: Exception | None = None
    for attempt in range(6):
        try:
            response = client.invoke_model(
                modelId=model_id,
                contentType="application/json",
                accept="application/json",
                body=json.dumps({"inputText": text}),
            )
            payload = json.loads(response["body"].read())
            embedding = payload.get("embedding")
            if not isinstance(embedding, list):
                raise RuntimeError("Bedrock embedding response missing 'embedding' array")
            return embedding
        except ClientError as exc:
            code = exc.response.get("Error", {}).get("Code", "")
            if code not in {"ThrottlingException", "ServiceUnavailableException"}:
                raise
            last_error = exc
            time.sleep(min(2**attempt, 30))
    raise RuntimeError(f"Bedrock embed throttled after retries: {last_error}") from last_error


def _put_vectors(client: Any, config: Config, vectors: list[dict[str, Any]]) -> None:
    client.put_vectors(
        vectorBucketName=config.vector_bucket,
        indexName=config.vector_index,
        vectors=vectors,
    )


def ingest_articles(config: Config, articles: list[Article] | None = None) -> dict[str, Any]:
    """Fetch (if needed), upload to S3, embed, and store vectors."""

    items = articles if articles is not None else fetch_articles()
    s3 = boto3.client("s3", region_name=config.aws_region)
    bedrock = boto3.client("bedrock-runtime", region_name=config.aws_region)
    s3vectors = boto3.client("s3vectors", region_name=config.aws_region)

    vectors: list[dict[str, Any]] = []
    fetched_at = datetime.now(timezone.utc)

    for article in items:
        document = article.format_document(fetched_at)
        s3.put_object(
            Bucket=config.source_bucket,
            Key=f"{config.documents_prefix}{article.filename}",
            Body=document.encode("utf-8"),
            ContentType="text/plain; charset=utf-8",
        )

        embedding = _bedrock_embed(bedrock, config.embedding_model_id, article.body)
        time.sleep(0.15)
        vectors.append(
            {
                "key": f"article-{article.url_hash}-chunk-000",
                "data": {"float32": embedding},
                "metadata": {
                    "source": article.filename,
                    "title": article.title,
                    "url": article.url,
                    "published": article.published,
                    "feed": article.feed,
                    "chunk": "0",
                },
            }
        )

    _put_vectors(s3vectors, config, vectors)

    marker = {
        "ingested_at": fetched_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "article_count": len(items),
    }
    s3.put_object(
        Bucket=config.source_bucket,
        Key=config.last_ingest_key,
        Body=json.dumps(marker).encode("utf-8"),
        ContentType="application/json",
    )

    return {
        "article_count": len(items),
        "ingested_at": marker["ingested_at"],
        "filenames": [article.filename for article in items],
    }


def ingest_status(config: Config) -> dict[str, Any]:
    """Return corpus stats from S3."""

    s3 = boto3.client("s3", region_name=config.aws_region)
    paginator = s3.get_paginator("list_objects_v2")

    article_count = 0
    for page in paginator.paginate(Bucket=config.source_bucket, Prefix=config.documents_prefix):
        for obj in page.get("Contents", []):
            key = obj["Key"]
            if key.endswith(".txt"):
                article_count += 1

    last_ingested_at: str | None = None
    try:
        response = s3.get_object(Bucket=config.source_bucket, Key=config.last_ingest_key)
        marker = json.loads(response["Body"].read().decode("utf-8"))
        last_ingested_at = marker.get("ingested_at")
        if marker.get("article_count") is not None:
            article_count = int(marker["article_count"])
    except ClientError as exc:
        if exc.response.get("Error", {}).get("Code") != "NoSuchKey":
            raise

    return {
        "article_count": article_count,
        "last_ingested_at": last_ingested_at,
    }


def load_document_from_s3(config: Config, source_key: str) -> tuple[dict[str, str], str]:
    """Load a corpus document and parsed headers from S3."""

    s3 = boto3.client("s3", region_name=config.aws_region)
    response = s3.get_object(
        Bucket=config.source_bucket,
        Key=f"{config.documents_prefix}{source_key}",
    )
    text = response["Body"].read().decode("utf-8")
    return parse_document_headers(text), document_body(text)
