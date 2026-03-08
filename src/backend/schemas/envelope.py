from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class ErrorBody(BaseModel):
    code: str
    message: str


class MetaBody(BaseModel):
    request_id: str


class Envelope(BaseModel, Generic[T]):
    data: T | None
    error: ErrorBody | None
    meta: MetaBody
