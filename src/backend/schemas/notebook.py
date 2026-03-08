from __future__ import annotations

from pydantic import BaseModel, Field


class NotebookCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=1000)


class NotebookUpdateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=1000)


class NotebookSummary(BaseModel):
    id: str
    title: str
    description: str | None
    is_default: bool
    created_at: str
    updated_at: str
