from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from io import BytesIO
from typing import Any

import fitz

from app.db.models import ChatMessage, ChatSession, Notebook


@dataclass(frozen=True)
class ExportSourceRecord:
    id: str
    title: str
    source_type: str
    status: str
    path_or_url: str
    metadata: dict[str, Any]


@dataclass(frozen=True)
class ExportChunkRecord:
    id: str
    source_id: str
    chunk_index: int
    text: str
    citation: dict[str, Any]


@dataclass(frozen=True)
class ExportContext:
    attached_source_ids: list[str]
    top_k: int | None
    similarity_threshold: float | None
    model: str | None
    memory_enabled: bool | None


class ChatExportService:
    def render_markdown(
        self,
        *,
        session: ChatSession,
        notebook: Notebook,
        messages: list[ChatMessage],
        sources: dict[str, ExportSourceRecord],
        chunks: dict[str, ExportChunkRecord],
        context: ExportContext,
    ) -> str:
        lines: list[str] = []
        lines.extend(_render_header(session=session, notebook=notebook))
        lines.extend(_render_query_context(context=context, sources=sources))
        for message in messages:
            lines.extend(_render_message(message=message, sources=sources, chunks=chunks))
        lines.extend(_render_sources_appendix(sources=sources))
        return "\n".join(lines).strip() + "\n"

    def render_pdf(self, markdown_text: str) -> bytes:
        doc = fitz.open()
        page = doc.new_page()
        font_size = 11
        line_height = 14
        margin = 48
        max_width = page.rect.width - (margin * 2)
        y = margin
        for raw_line in markdown_text.splitlines():
            for line in _wrap_line(raw_line, max_width, font_size):
                if y > page.rect.height - margin:
                    page = doc.new_page()
                    y = margin
                page.insert_text((margin, y), line, fontsize=font_size)
                y += line_height
        buffer = BytesIO()
        doc.save(buffer)
        return buffer.getvalue()


def _wrap_line(text: str, max_width: float, font_size: int) -> list[str]:
    if not text:
        return [""]
    words = text.split(" ")
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if _estimate_width(candidate, font_size) <= max_width:
            current = candidate
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def _estimate_width(text: str, font_size: int) -> float:
    return len(text) * (font_size * 0.55)


def _render_header(*, session: ChatSession, notebook: Notebook) -> list[str]:
    return [
        f"# {notebook.title} — Research Report",
        "",
        f"Session: {session.title}",
        f"Exported: {datetime.utcnow().isoformat()}Z",
        "",
    ]


def _render_query_context(*, context: ExportContext, sources: dict[str, ExportSourceRecord]) -> list[str]:
    lines: list[str] = ["## Query Context", ""]
    lines.append(f"Retrieval top_k: {_format_optional(context.top_k)}")
    lines.append(f"Similarity threshold: {_format_optional(context.similarity_threshold)}")
    lines.append(f"Model: {_format_optional(context.model)}")
    lines.append(f"Memory enabled: {_format_optional(context.memory_enabled)}")
    lines.append("")
    if context.attached_source_ids:
        lines.append("Attached sources:")
        for source_id in context.attached_source_ids:
            source = sources.get(source_id)
            if source is None:
                lines.append(f"- {source_id}")
            else:
                lines.append(f"- {source.title} ({source.source_type}, {source_id})")
    else:
        lines.append("Attached sources: none")
    lines.append("")
    return lines


def _render_message(
    *,
    message: ChatMessage,
    sources: dict[str, ExportSourceRecord],
    chunks: dict[str, ExportChunkRecord],
) -> list[str]:
    role = "User" if message.role == "user" else "Assistant"
    lines: list[str] = [f"## {role}", message.content.strip(), ""]
    if not message.citations_json:
        return lines
    lines.append("Citations:")
    for citation in message.citations_json:
        lines.extend(_render_citation(citation=citation, sources=sources, chunks=chunks))
    lines.append("")
    return lines


def _render_citation(
    *,
    citation: dict[str, Any],
    sources: dict[str, ExportSourceRecord],
    chunks: dict[str, ExportChunkRecord],
) -> list[str]:
    chunk_id = str(citation.get("chunk_id") or "")
    source_id = str(citation.get("source_id") or "")
    page = citation.get("page_number")
    excerpt = str(citation.get("excerpt") or "")
    label = _format_citation_label(source_id=source_id, chunk_id=chunk_id, page=page, sources=sources)
    lines = [f"- {label}"]
    if excerpt:
        lines.append(f"  - Excerpt: {excerpt}")
    chunk = chunks.get(chunk_id)
    if chunk is not None:
        chunk_text, truncated = _truncate_text(chunk.text, limit=2000)
        suffix = " (truncated)" if truncated else ""
        lines.append(f"  - Cited data{suffix}:")
        lines.extend([f"    {line}" for line in chunk_text.splitlines() if line.strip()])
    return lines


def _render_sources_appendix(*, sources: dict[str, ExportSourceRecord]) -> list[str]:
    if not sources:
        return []
    lines = ["## Sources Appendix", ""]
    for source in sorted(sources.values(), key=lambda item: item.title.lower()):
        lines.append(f"- {source.title} ({source.source_type})")
        lines.append(f"  - id: {source.id}")
        lines.append(f"  - status: {source.status}")
        lines.append(f"  - path_or_url: {source.path_or_url}")
        if source.metadata:
            lines.append(f"  - metadata: {source.metadata}")
    lines.append("")
    return lines


def _format_optional(value: Any) -> str:
    return "not provided" if value is None else str(value)


def _format_citation_label(
    *,
    source_id: str,
    chunk_id: str,
    page: Any,
    sources: dict[str, ExportSourceRecord],
) -> str:
    source = sources.get(source_id)
    source_label = source.title if source is not None else source_id
    label = f"{source_label} (source:{source_id}, chunk:{chunk_id})"
    if page is not None:
        label += f", page:{page}"
    return label


def _truncate_text(text: str, *, limit: int) -> tuple[str, bool]:
    if len(text) <= limit:
        return text, False
    return text[:limit].rstrip(), True
