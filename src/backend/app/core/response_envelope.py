from __future__ import annotations

from typing import Any

from fastapi.responses import JSONResponse


def success_response(data: Any, request_id: str, status_code: int = 200) -> JSONResponse:
    payload = {
        "data": data,
        "error": None,
        "meta": {"request_id": request_id},
    }
    return JSONResponse(content=payload, status_code=status_code)


def error_response(
    code: str,
    message: str,
    request_id: str,
    status_code: int = 400,
    details: dict[str, Any] | list[dict[str, Any]] | None = None,
) -> JSONResponse:
    error: dict[str, Any] = {"code": code, "message": message}
    if details is not None:
        error["details"] = details
    payload = {
        "data": None,
        "error": error,
        "meta": {"request_id": request_id},
    }
    return JSONResponse(content=payload, status_code=status_code)
