from __future__ import annotations

from pydantic import BaseModel, Field


class CreatePodcastRequest(BaseModel):
    source_ids: list[str] = Field(min_length=1)
    title: str = Field(default="NotebookLM Podcast", min_length=1, max_length=255)
    voice: str | None = Field(default=None, max_length=64)


class RetryPodcastRequest(BaseModel):
    title: str = Field(default="NotebookLM Podcast Retry", min_length=1, max_length=255)
    voice: str | None = Field(default=None, max_length=64)


class PodcastOut(BaseModel):
    id: str
    voice: str | None
    status: str
    script: str | None
    output_path: str | None
    duration_ms: int | None
    error_message: str | None
