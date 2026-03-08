from __future__ import annotations

from pydantic import BaseModel, Field

from schemas.citation import Citation


class CreateSessionRequest(BaseModel):
    title: str = Field(default="New Session", min_length=1, max_length=255)


class ChatSessionOut(BaseModel):
    id: str
    title: str
    created_at: str
    updated_at: str


class ChatMessageRequest(BaseModel):
    message: str = Field(min_length=1, max_length=5000)
    source_ids: list[str] = Field(default_factory=list)


class ChatMessageOut(BaseModel):
    id: str
    role: str
    content: str
    citations: list[Citation]
    model_info: dict[str, str]
    created_at: str
