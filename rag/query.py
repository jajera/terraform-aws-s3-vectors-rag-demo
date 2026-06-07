"""RAG query: embed question, retrieve/rerank, generate grounded answer."""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

import boto3

from rag.config import Config
from rag.ingest import load_document_from_s3

MAX_CONTEXT_CHARS = 8_000
MIN_TOP_K = 3
MAX_TOP_K = 8
RETRIEVAL_MULTIPLIER = 3
RECENCY_HALF_LIFE_DAYS = 30.0


@dataclass(frozen=True)
class SourceMatch:
    key: str
    title: str
    url: str
    published: str
    feed: str
    source: str
    excerpt: str


@dataclass(frozen=True)
class QueryResult:
    question: str
    answer: str
    sources: list[SourceMatch]


@dataclass
class _Candidate:
    source: SourceMatch
    body: str
    snippet: str
    similarity_score: float
    recency_score: float
    final_score: float
    published_dt: datetime | None


def _bedrock_embed(client: Any, model_id: str, text: str) -> list[float]:
    response = client.invoke_model(
        modelId=model_id,
        contentType="application/json",
        accept="application/json",
        body=json.dumps({"inputText": text}),
    )
    payload = json.loads(response["body"].read())
    return payload["embedding"]


def _bedrock_llm(client: Any, model_id: str, context: str, question: str, source_count: int) -> str:
    body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 1024,
        "messages": [
            {
                "role": "user",
                "content": (
                    "You are an AWS news briefing assistant. Use only the provided context.\n"
                    "If the context is insufficient, state that clearly and do not guess.\n\n"
                    "Output markdown using this structure:\n"
                    "## Direct answer\n"
                    "(2-5 sentences)\n\n"
                    "## What is known\n"
                    "- Bullet points with citations like [1], [2]\n\n"
                    "## What is unclear\n"
                    "- Bullet points for missing facts or uncertainty\n\n"
                    "## Sources used\n"
                    "- [n] short source title\n\n"
                    f"There are {source_count} sources in context. Every factual bullet must cite at least one source.\n\n"
                    f"Context:\n{context}\n\nQuestion: {question}"
                ),
            }
        ],
    }
    response = client.invoke_model(
        modelId=model_id,
        contentType="application/json",
        accept="application/json",
        body=json.dumps(body),
    )
    payload = json.loads(response["body"].read())
    content = payload.get("content", [])
    if not content:
        return ""
    return content[0].get("text", "")


def _parse_iso_datetime(value: str) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError:
        return None


def _extract_time_window_days(question: str) -> int | None:
    text = question.lower()

    match = re.search(r"\b(?:last|past)\s+(\d+)\s*(day|days|week|weeks|month|months)\b", text)
    if match:
        amount = max(1, int(match.group(1)))
        unit = match.group(2)
        if "day" in unit:
            return amount
        if "week" in unit:
            return amount * 7
        return amount * 30

    if "last week" in text or "past week" in text:
        return 7
    if "last month" in text or "past month" in text:
        return 30
    if "last 2 weeks" in text or "past 2 weeks" in text:
        return 14
    return None


def _is_broad_query(question: str) -> bool:
    text = question.lower()
    broad_markers = (
        "summarize",
        "summary",
        "highlights",
        "latest",
        "recent",
        "what's new",
        "whats new",
        "news",
        "updates",
    )
    return any(marker in text for marker in broad_markers) or len(text.split()) >= 12


def _adaptive_top_k(question: str, requested_top_k: int) -> int:
    target = max(MIN_TOP_K, requested_top_k)
    if _extract_time_window_days(question) is not None:
        target = max(target, 6)
    elif _is_broad_query(question):
        target = max(target, 5)
    return min(target, MAX_TOP_K)


def _tokenize(text: str) -> set[str]:
    return {token for token in re.findall(r"[a-z0-9]+", text.lower()) if len(token) > 2}


def _best_snippet(body: str, question: str, max_chars: int = 700) -> str:
    paragraphs = [part.strip() for part in body.split("\n\n") if part.strip()]
    if not paragraphs:
        return ""

    question_terms = _tokenize(question)
    scored: list[tuple[int, int, str]] = []
    for paragraph in paragraphs:
        terms = _tokenize(paragraph)
        overlap = len(question_terms.intersection(terms))
        scored.append((overlap, len(paragraph), paragraph))

    scored.sort(key=lambda row: (row[0], row[1]), reverse=True)

    chosen: list[str] = []
    total = 0
    for overlap, _, paragraph in scored:
        if overlap == 0 and chosen:
            break
        remaining = max_chars - total
        if remaining <= 0:
            break
        snippet_part = paragraph[:remaining]
        if len(paragraph) > remaining:
            snippet_part = snippet_part.rstrip() + "..."
        chosen.append(snippet_part)
        total += len(snippet_part) + 2
        if total >= max_chars:
            break

    if not chosen:
        head = body[:max_chars]
        return head + ("..." if len(body) > max_chars else "")

    return "\n\n".join(chosen)


def _vector_similarity_score(vector: dict[str, Any]) -> float:
    if isinstance(vector.get("similarity"), (int, float)):
        return float(vector["similarity"])
    if isinstance(vector.get("score"), (int, float)):
        return float(vector["score"])
    if isinstance(vector.get("distance"), (int, float)):
        return 1.0 / (1.0 + float(vector["distance"]))
    return 0.0


def _recency_score(published_dt: datetime | None) -> float:
    if published_dt is None:
        return 0.25
    age_days = max((datetime.now(timezone.utc) - published_dt).total_seconds() / 86_400.0, 0.0)
    return math.exp(-age_days / RECENCY_HALF_LIFE_DAYS)


def _dedupe_key(source_file: str, title: str, url: str) -> str:
    normalized = (url or "").strip().lower() or (title or "").strip().lower() or source_file
    return normalized


def _build_context(candidates: list[_Candidate], max_chars: int = MAX_CONTEXT_CHARS) -> str:
    blocks: list[str] = []
    total = 0
    for idx, candidate in enumerate(candidates, start=1):
        block = (
            f"[{idx}] Title: {candidate.source.title}\n"
            f"[{idx}] URL: {candidate.source.url}\n"
            f"[{idx}] Published: {candidate.source.published}\n"
            f"[{idx}] Feed: {candidate.source.feed}\n"
            f"[{idx}] Snippet:\n{candidate.snippet}\n"
        )
        if total + len(block) > max_chars:
            break
        blocks.append(block)
        total += len(block)
    return "\n---\n".join(blocks)


def ask(config: Config, question: str, top_k: int = 3) -> QueryResult:
    """Run the full RAG query pipeline."""

    bedrock = boto3.client("bedrock-runtime", region_name=config.aws_region)
    s3vectors = boto3.client("s3vectors", region_name=config.aws_region)

    desired_top_k = _adaptive_top_k(question, top_k)
    retrieval_top_k = min(desired_top_k * RETRIEVAL_MULTIPLIER, 20)
    time_window_days = _extract_time_window_days(question)
    cutoff = datetime.now(timezone.utc) - timedelta(days=time_window_days) if time_window_days else None

    query_embedding = _bedrock_embed(bedrock, config.embedding_model_id, question)
    response = s3vectors.query_vectors(
        vectorBucketName=config.vector_bucket,
        indexName=config.vector_index,
        queryVector={"float32": query_embedding},
        topK=retrieval_top_k,
        returnMetadata=True,
    )

    doc_cache: dict[str, tuple[dict[str, str], str]] = {}
    candidates: list[_Candidate] = []
    seen: set[str] = set()

    for vector in response.get("vectors", []):
        metadata = vector.get("metadata") or {}
        source_file = metadata.get("source", "")
        if not source_file:
            continue

        if source_file not in doc_cache:
            doc_cache[source_file] = load_document_from_s3(config, source_file)
        headers, body = doc_cache[source_file]

        title = metadata.get("title") or headers.get("title", source_file)
        url = metadata.get("url") or headers.get("url", "")
        published = metadata.get("published") or headers.get("published", "")
        feed = metadata.get("feed") or headers.get("feed", "")
        published_dt = _parse_iso_datetime(published)

        if cutoff and published_dt and published_dt < cutoff:
            continue

        unique_key = _dedupe_key(source_file, title, url)
        if unique_key in seen:
            continue
        seen.add(unique_key)

        snippet = _best_snippet(body, question, max_chars=700)
        similarity = _vector_similarity_score(vector)
        freshness = _recency_score(published_dt)
        final = (0.8 * similarity) + (0.2 * freshness)
        excerpt = snippet[:500] + ("..." if len(snippet) > 500 else "")

        candidates.append(
            _Candidate(
                source=SourceMatch(
                    key=vector.get("key", ""),
                    title=title,
                    url=url,
                    published=published,
                    feed=feed,
                    source=source_file,
                    excerpt=excerpt,
                ),
                body=body,
                snippet=snippet,
                similarity_score=similarity,
                recency_score=freshness,
                final_score=final,
                published_dt=published_dt,
            )
        )

    candidates.sort(key=lambda candidate: candidate.final_score, reverse=True)
    selected = candidates[:desired_top_k]
    sources = [candidate.source for candidate in selected]

    if not selected:
        fallback = (
            "## Direct answer\n"
            "I don't have enough information in the indexed announcements to answer that yet.\n\n"
            "## What is known\n"
            "- No matching announcements were retrieved from the current corpus.\n\n"
            "## What is unclear\n"
            "- The answer would require additional or newer source documents.\n\n"
            "## Sources used\n"
            "- None"
        )
        return QueryResult(question=question, answer=fallback, sources=[])

    context = _build_context(selected, max_chars=MAX_CONTEXT_CHARS)
    answer = _bedrock_llm(bedrock, config.llm_model_id, context, question, source_count=len(selected))

    return QueryResult(question=question, answer=answer, sources=sources)
