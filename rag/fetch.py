"""Fetch AWS announcements from public RSS feeds."""

from __future__ import annotations

import argparse
import hashlib
import html
import re
import time
import unicodedata
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

USER_AGENT = (
    "terraform-aws-s3-vectors-rag-demo/1.0 "
    "(https://github.com/jajera/terraform-aws-s3-vectors-rag-demo; AWS news corpus)"
)

MAX_BODY_CHARS = 8000
MIN_ARTICLES = 5

# Per-feed limits match what the public RSS endpoints expose (~100 What's New, ~20 blog).
FEEDS = (
    ("aws-whats-new", "https://aws.amazon.com/about-aws/whats-new/recent/feed/", 100),
    ("aws-news-blog", "https://aws.amazon.com/blogs/aws/feed/", 20),
)


@dataclass(frozen=True)
class Article:
    feed: str
    title: str
    url: str
    published: str
    body: str
    filename: str
    url_hash: str

    def format_document(self, fetched_at: datetime | None = None) -> str:
        fetched = (fetched_at or datetime.now(timezone.utc)).strftime("%Y-%m-%dT%H:%M:%SZ")
        header = (
            f"# Title: {self.title}\n"
            f"# URL: {self.url}\n"
            f"# Published: {self.published}\n"
            f"# Feed: {self.feed}\n"
            f"# Fetched: {fetched}\n"
            "\n"
        )
        return header + self.body


class _HTMLTextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._parts: list[str] = []

    def handle_data(self, data: str) -> None:
        if data.strip():
            self._parts.append(data.strip())

    def get_text(self) -> str:
        return " ".join(self._parts)


def _strip_html(value: str) -> str:
    if not value:
        return ""
    unescaped = html.unescape(value)
    parser = _HTMLTextExtractor()
    parser.feed(unescaped)
    parser.close()
    text = parser.get_text() or re.sub(r"<[^>]+>", " ", unescaped)
    return re.sub(r"\s+", " ", text).strip()


def _normalize_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text)
    return normalized.encode("ascii", "ignore").decode("ascii")


def _truncate_body(text: str) -> str:
    if len(text) <= MAX_BODY_CHARS:
        return text
    trimmed = text[:MAX_BODY_CHARS].rsplit(" ", 1)[0]
    return trimmed + "\n\n[Truncated for demo embedding size.]\n"


def _parse_published(value: str | None) -> str:
    if not value:
        return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    try:
        dt = parsedate_to_datetime(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    except (TypeError, ValueError, OverflowError):
        return value.strip()


def _url_hash(url: str) -> str:
    return hashlib.sha256(url.encode("utf-8")).hexdigest()[:8]


def _filename_for(feed: str, url: str) -> str:
    return f"{feed}-{_url_hash(url)}.txt"


def _local_name(tag: str) -> str:
    if "}" in tag:
        return tag.rsplit("}", 1)[-1]
    return tag


def _child_text(parent: ET.Element, name: str) -> str:
    for child in parent:
        if _local_name(child.tag) == name and child.text:
            return child.text.strip()
    return ""


def _fetch_bytes(url: str, retries: int = 2) -> bytes:
    request = Request(url, headers={"User-Agent": USER_AGENT})
    last_error: Exception | None = None
    for attempt in range(retries):
        try:
            with urlopen(request, timeout=60) as response:
                return response.read()
        except (HTTPError, URLError, TimeoutError) as exc:
            last_error = exc
            if attempt + 1 < retries:
                time.sleep(2)
    raise RuntimeError(f"Failed to fetch {url}: {last_error}") from last_error


def _parse_rss_items(xml_bytes: bytes, limit: int) -> list[dict[str, str]]:
    root = ET.fromstring(xml_bytes)
    channel = root.find("channel")
    if channel is None:
        channel = root

    items: list[dict[str, str]] = []
    for item in channel.findall("item"):
        title = _child_text(item, "title")
        link = _child_text(item, "link")
        if not title or not link:
            continue
        description = _child_text(item, "description")
        content = ""
        for child in item:
            if _local_name(child.tag) == "encoded" and child.text:
                content = child.text.strip()
                break
        body_source = content or description or title
        items.append(
            {
                "title": title,
                "url": link,
                "published": _parse_published(_child_text(item, "pubDate")),
                "body": _truncate_body(_normalize_text(_strip_html(body_source))),
            }
        )
        if len(items) >= limit:
            break
    return items


def fetch_articles() -> list[Article]:
    """Download and deduplicate articles from configured RSS feeds."""

    seen_urls: set[str] = set()
    articles: list[Article] = []

    for index, (feed_id, feed_url, limit) in enumerate(FEEDS):
        if index > 0:
            time.sleep(1)
        raw = _fetch_bytes(feed_url)
        for item in _parse_rss_items(raw, limit):
            url = item["url"]
            if url in seen_urls:
                continue
            seen_urls.add(url)
            url_hash = _url_hash(url)
            articles.append(
                Article(
                    feed=feed_id,
                    title=item["title"],
                    url=url,
                    published=item["published"],
                    body=item["body"],
                    filename=_filename_for(feed_id, url),
                    url_hash=url_hash,
                )
            )

    if len(articles) < MIN_ARTICLES:
        raise RuntimeError(
            f"Fetched only {len(articles)} articles; need at least {MIN_ARTICLES}. "
            "Check network access and RSS feed availability."
        )
    return articles


def write_articles_to_dir(articles: list[Article], corpus_dir: Path) -> None:
    """Write articles as .txt files under corpus_dir."""

    corpus_dir.mkdir(parents=True, exist_ok=True)
    for path in corpus_dir.glob("*.txt"):
        path.unlink()
    fetched_at = datetime.now(timezone.utc)
    for article in articles:
        dest = corpus_dir / article.filename
        dest.write_text(article.format_document(fetched_at), encoding="utf-8")


def parse_document_headers(text: str) -> dict[str, str]:
    """Parse # Key: value headers from a corpus document."""

    headers: dict[str, str] = {}
    for line in text.splitlines():
        if not line.startswith("# "):
            break
        if ":" not in line:
            continue
        key, value = line[2:].split(":", 1)
        headers[key.strip().lower()] = value.strip()
    return headers


def document_body(text: str) -> str:
    """Return document body without the leading header block."""

    lines = text.splitlines()
    for index, line in enumerate(lines):
        if not line.startswith("#") and line.strip() == "":
            return "\n".join(lines[index + 1 :]).strip()
    return text.strip()


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch AWS news RSS corpus")
    parser.add_argument(
        "--write",
        type=Path,
        metavar="DIR",
        help="Write fetched articles to this directory",
    )
    args = parser.parse_args()

    articles = fetch_articles()
    if args.write:
        write_articles_to_dir(articles, args.write)
    print(f"Fetched {len(articles)} articles")
    for article in articles:
        print(f"  {article.filename}  {article.title[:72]}")


if __name__ == "__main__":
    main()
