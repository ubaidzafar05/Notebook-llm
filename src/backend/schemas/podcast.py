from __future__ import annotations

from pydantic import BaseModel, Field


class CreatePodcastRequest(BaseModel):
    source_ids: list[str] = Field(min_length=1)
    title: str = Field(default="NotebookLM Podcast", min_length=1, max_length=255)


class RetryPodcastRequest(BaseModel):
    title: str = Field(default="NotebookLM Podcast Retry", min_length=1, max_length=255)


class PodcastOut(BaseModel):
    id: str
    status: str
    output_path: str | None
    duration_ms: int | None
    error_message: str | None
