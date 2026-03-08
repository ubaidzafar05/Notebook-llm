from __future__ import annotations

import re

import requests
import trafilatura
from bs4 import BeautifulSoup

from app.core.config import get_settings
from app.core.exceptions import AppError
from app.ingestion.source_registry import ParsedSegment


def _clean_text(text: str) -> str:
    clean = re.sub(r"\s+", " ", text).strip()
    return clean


def parse_web_url(url: str) -> list[ParsedSegment]:
    settings = get_settings()
    if settings.firecrawl_api_key:
        firecrawl_result = _parse_with_firecrawl(url=url, api_key=settings.firecrawl_api_key)
        if firecrawl_result:
            return [firecrawl_result]

    downloaded = trafilatura.fetch_url(url)
    if downloaded:
        extracted = trafilatura.extract(downloaded, output_format="txt", include_comments=False)
        if extracted:
            cleaned = _clean_text(extracted)
            if cleaned:
                return [ParsedSegment(text=cleaned, citation={"url": url, "source": "web"})]

    try:
        response = requests.get(url, timeout=20)
    except requests.Timeout as exc:
        raise AppError(
            code="WEB_TIMEOUT",
            message=f"Timed out fetching URL: {url}",
            status_code=408,
            details={"failure_stage": "fetch"},
        ) from exc
    except requests.RequestException as exc:
        raise AppError(
            code="WEB_FETCH_FAILED",
            message=f"Unable to fetch URL: {url}",
            status_code=400,
            details={"failure_stage": "fetch"},
        ) from exc
    if response.status_code >= 400:
        raise AppError(
            code="WEB_FETCH_FAILED",
            message=f"Unable to fetch URL: {url}",
            status_code=400,
            details={"failure_stage": "fetch"},
        )

    soup = BeautifulSoup(response.text, "html.parser")
    text = _clean_text(soup.get_text(separator=" "))
    if not text:
        raise AppError(
            code="WEB_PARSE_FAILED",
            message="No parseable text found on URL",
            status_code=400,
            details={"failure_stage": "parse"},
        )
    return [ParsedSegment(text=text, citation={"url": url, "source": "web"})]


def _parse_with_firecrawl(url: str, api_key: str) -> ParsedSegment | None:
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {"url": url, "formats": ["markdown"]}
    response = requests.post("https://api.firecrawl.dev/v1/scrape", headers=headers, json=payload, timeout=30)
    if response.status_code >= 400:
        return None
    body = response.json()
    data = body.get("data", {})
    markdown = data.get("markdown")
    if not isinstance(markdown, str):
        return None
    cleaned = _clean_text(markdown)
    if not cleaned:
        return None
    return ParsedSegment(text=cleaned, citation={"url": url, "source": "web"})
