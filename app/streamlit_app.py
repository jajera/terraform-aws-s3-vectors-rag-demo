"""Streamlit UI for AWS News RAG briefing."""

from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import boto3
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from rag.config import load_config
from rag.ingest import ingest_status
from rag.query import ask

EXAMPLE_QUERIES = [
    "What did AWS announce recently about Amazon Bedrock?",
    "Summarize recent AWS storage announcements.",
    "What new generative AI features did AWS launch?",
]


def _format_relative_time(iso_timestamp: str | None) -> str:
    if not iso_timestamp:
        return "never"
    try:
        ingested = datetime.fromisoformat(iso_timestamp.replace("Z", "+00:00"))
        delta = datetime.now(timezone.utc) - ingested.astimezone(timezone.utc)
        hours = int(delta.total_seconds() // 3600)
        if hours < 1:
            minutes = int(delta.total_seconds() // 60)
            return f"{minutes}m ago" if minutes > 0 else "just now"
        if hours < 48:
            return f"{hours}h ago"
        days = hours // 24
        return f"{days}d ago"
    except ValueError:
        return iso_timestamp


def _invoke_ingest_lambda(config) -> dict:
    if not config.ingest_function_name:
        raise RuntimeError("INGEST_FUNCTION_NAME is not set")
    client = boto3.client("lambda", region_name=config.aws_region)
    response = client.invoke(
        FunctionName=config.ingest_function_name,
        InvocationType="RequestResponse",
        Payload=json.dumps({"source": "streamlit"}).encode("utf-8"),
    )
    payload = response["Payload"].read().decode("utf-8")
    if response.get("FunctionError"):
        raise RuntimeError(payload)
    outer = json.loads(payload)
    if "body" in outer:
        return json.loads(outer["body"])
    return outer


def _source_payload(sources) -> list[dict[str, str]]:
    return [
        {
            "title": source.title,
            "url": source.url,
            "published": source.published,
            "feed": source.feed,
            "excerpt": source.excerpt,
        }
        for source in sources
    ]


def _render_sources(sources: list[dict[str, str]], expanded: bool = False) -> None:
    with st.expander("Sources", expanded=expanded):
        for index, source in enumerate(sources, start=1):
            if source["url"]:
                st.markdown(f"{index}. **[{source['title']}]({source['url']})**")
            else:
                st.markdown(f"{index}. **{source['title']}**")
            st.caption(f"{source['feed']} · {source['published']}")
            st.write(source["excerpt"])


def main() -> None:
    st.set_page_config(page_title="AWS News Briefing", layout="wide")

    col_title, col_sources = st.columns([2, 1])
    with col_title:
        st.title("AWS News Briefing")
        st.caption("Answers grounded in live AWS What's New and AWS News Blog announcements.")

    try:
        config = load_config()
    except RuntimeError as exc:
        st.error(str(exc))
        st.info("Run `source scripts/export-env.sh` from the repository root after `terraform apply`.")
        st.stop()

    status = ingest_status(config)

    with st.sidebar:
        st.subheader("Corpus")
        st.metric("Articles indexed", status["article_count"])
        st.write(f"Last ingested: **{_format_relative_time(status['last_ingested_at'])}**")
        if st.button("Refresh Now", type="primary", use_container_width=True):
            with st.spinner("Fetching RSS and re-indexing..."):
                try:
                    result = _invoke_ingest_lambda(config)
                    st.success(f"Ingested {result.get('article_count', '?')} articles.")
                    time.sleep(1)
                    st.rerun()
                except Exception as exc:
                    st.error(f"Ingest failed: {exc}")
        st.divider()
        st.markdown("**Example questions**")
        for query in EXAMPLE_QUERIES:
            if st.button(query, use_container_width=True, key=f"example-{query}"):
                st.session_state["pending_query"] = query

    with col_sources:
        st.subheader("Latest retrieval")
        latest_sources = st.session_state.get("latest_sources", [])
        if latest_sources:
            for source in latest_sources:
                if source["url"]:
                    st.markdown(f"**[{source['title']}]({source['url']})**")
                else:
                    st.markdown(f"**{source['title']}**")
                st.caption(f"{source['feed']} · {source['published']}")
        else:
            st.write("Ask a question to see matched announcements.")

    if "messages" not in st.session_state:
        st.session_state.messages = []

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if message["role"] == "assistant" and message.get("sources"):
                _render_sources(message["sources"])

    prompt = st.chat_input("Ask about recent AWS announcements...")
    if st.session_state.get("pending_query"):
        prompt = st.session_state.pop("pending_query")

    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            if status["article_count"] == 0:
                st.warning("Corpus is empty. Click **Refresh Now** in the sidebar or wait for ingest to finish.")
            else:
                with st.spinner("Searching announcements and generating answer..."):
                    try:
                        result = ask(config, prompt)
                        sources = _source_payload(result.sources)
                        st.markdown(result.answer)
                        _render_sources(sources, expanded=True)
                        st.session_state.latest_sources = sources
                        st.session_state.messages.append(
                            {
                                "role": "assistant",
                                "content": result.answer,
                                "sources": sources,
                            }
                        )
                    except Exception as exc:
                        st.error(f"Query failed: {exc}")


if __name__ == "__main__":
    main()
