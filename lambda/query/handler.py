"""API Gateway handler for RAG query, status, and admin ingest."""

from __future__ import annotations

import json
import os
import sys
from dataclasses import asdict

sys.path.insert(0, os.path.dirname(__file__))

import boto3

from rag.config import Config
from rag.ingest import ingest_status
from rag.query import ask

ADMIN_GROUP = "admins"
CORS_ORIGIN = os.environ.get("CORS_ALLOW_ORIGIN", "")


def _config_from_env() -> Config:
    region = os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION")
    if not region:
        raise RuntimeError("AWS_REGION is not available")
    return Config(
        aws_region=region,
        source_bucket=os.environ["SOURCE_BUCKET"],
        vector_bucket=os.environ["VECTOR_BUCKET"],
        vector_index=os.environ["VECTOR_INDEX"],
        embedding_model_id=os.environ["EMBEDDING_MODEL_ID"],
        llm_model_id=os.environ["LLM_MODEL_ID"],
        ingest_function_name=os.environ.get("INGEST_FUNCTION_NAME"),
    )


def _headers(extra: dict[str, str] | None = None) -> dict[str, str]:
    base = {
        "Content-Type": "application/json",
    }
    if CORS_ORIGIN:
        base["Access-Control-Allow-Origin"] = CORS_ORIGIN
        base["Access-Control-Allow-Headers"] = "Authorization,Content-Type"
        base["Access-Control-Allow-Methods"] = "GET,POST,OPTIONS"
    if extra:
        base.update(extra)
    return base


def _response(status: int, body: dict) -> dict:
    return {
        "statusCode": status,
        "headers": _headers(),
        "body": json.dumps(body),
    }


def _claims(event: dict) -> dict:
    authorizer = event.get("requestContext", {}).get("authorizer", {})
    jwt_claims = authorizer.get("jwt", {}).get("claims", {})
    return jwt_claims if isinstance(jwt_claims, dict) else {}


def _normalize_groups(raw) -> list[str]:
    if isinstance(raw, list):
        return [str(g).strip() for g in raw if str(g).strip()]
    if not raw:
        return []
    text = str(raw).strip()
    if text.startswith("[") and text.endswith("]"):
        inner = text[1:-1].strip()
        if inner:
            return [g.strip() for g in inner.split(",") if g.strip()]
        return []
    if text.startswith("["):
        try:
            parsed = json.loads(text)
            if isinstance(parsed, list):
                return [str(g).strip() for g in parsed if str(g).strip()]
        except json.JSONDecodeError:
            pass
    return [g.strip() for g in text.split(",") if g.strip()]


def _is_admin(event: dict) -> bool:
    claims = _claims(event)
    return ADMIN_GROUP in _normalize_groups(claims.get("cognito:groups"))


def _route(event: dict) -> tuple[str, str]:
    ctx = event.get("requestContext", {})
    route_key = ctx.get("routeKey", "")
    if route_key and route_key != "$default":
        method, path = route_key.split(" ", 1)
        return method.upper(), path
    return event.get("requestContext", {}).get("http", {}).get("method", "GET").upper(), event.get(
        "rawPath", "/"
    )


def _body(event: dict) -> dict:
    raw = event.get("body") or "{}"
    if event.get("isBase64Encoded"):
        import base64

        raw = base64.b64decode(raw).decode("utf-8")
    return json.loads(raw) if raw else {}


def handler(event, context):
    method, path = _route(event)

    if method == "OPTIONS":
        return {"statusCode": 204, "headers": _headers(), "body": ""}

    config = _config_from_env()

    if path == "/status" and method == "GET":
        return _response(200, ingest_status(config))

    if path == "/query" and method == "POST":
        payload = _body(event)
        question = (payload.get("question") or "").strip()
        if not question:
            return _response(400, {"error": "question is required"})
        if len(question) > 4000:
            return _response(400, {"error": "question too long"})
        result = ask(config, question)
        return _response(
            200,
            {
                "question": result.question,
                "answer": result.answer,
                "sources": [asdict(source) for source in result.sources],
            },
        )

    if path == "/ingest" and method == "POST":
        if not _is_admin(event):
            return _response(403, {"error": "admin access required"})
        function_name = config.ingest_function_name
        if not function_name:
            return _response(500, {"error": "ingest function not configured"})
        client = boto3.client("lambda", region_name=config.aws_region)
        client.invoke(
            FunctionName=function_name,
            InvocationType="Event",
            Payload=json.dumps({"source": "api"}).encode("utf-8"),
        )
        return _response(202, {"message": "ingest started"})

    return _response(404, {"error": "not found"})
