from __future__ import annotations

from pydantic import BaseModel, Field, HttpUrl


class SourceCreateUrlRequest(BaseModel):
    url: HttpUrl
    source_type: str = Field(pattern="^(web|youtube)$")


class SourceOut(BaseModel):
    id: str
    name: str
    source_type: str
    status: str
    path_or_url: str
    metadata: dict[str, str | int | float | None]


class JobOut(BaseModel):
    id: str
    status: str
    job_type: str
    queue_job_id: str | None = None
    queue_name: str | None = None
    dead_lettered: bool = False
    failure_code: str | None = None
    cancel_requested: bool = False
    result: dict[str, str | int | float | bool | None]
    error_message: str | None


class SourceChunkOut(BaseModel):
    chunk_id: str
    chunk_index: int
    excerpt: str
    citation: dict[str, str | int | float | None]
