"""Stable API response contracts.

These dataclasses intentionally avoid web-framework dependencies so the same
contract can be used by FastAPI handlers, tests, and background jobs.
"""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from typing import Any
from uuid import uuid4

from app.agents.schemas import utc_now
from app.core.errors import AppError


@dataclass(frozen=True)
class ResponseMeta:
    """Metadata included in every API response."""

    request_id: str
    timestamp: datetime
    trace_id: str | None = None

    @classmethod
    def create(cls, request_id: str | None = None) -> "ResponseMeta":
        return cls(request_id=request_id or str(uuid4()), timestamp=utc_now())


@dataclass(frozen=True)
class ApiError:
    """Client-facing error payload."""

    code: str
    message: str
    details: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_app_error(cls, error: AppError) -> "ApiError":
        return cls(code=error.code, message=error.message, details=error.safe_details)


@dataclass(frozen=True)
class ApiResponse:
    """Common response envelope for successful and failed calls."""

    data: dict[str, Any] | list[Any] | None
    error: ApiError | None
    meta: ResponseMeta

    @classmethod
    def ok(
        cls,
        data: dict[str, Any] | list[Any] | None,
        *,
        request_id: str | None = None,
    ) -> "ApiResponse":
        return cls(data=data, error=None, meta=ResponseMeta.create(request_id))

    @classmethod
    def failed(cls, error: AppError, *, request_id: str | None = None) -> "ApiResponse":
        return cls(
            data=None,
            error=ApiError.from_app_error(error),
            meta=ResponseMeta.create(request_id),
        )

    def to_dict(self) -> dict[str, Any]:
        error = None
        if self.error is not None:
            error = {
                "code": self.error.code,
                "message": self.error.message,
                "details": self.error.details,
            }

        return {
            "data": self.data,
            "error": error,
            "meta": {
                "request_id": self.meta.request_id,
                "trace_id": self.meta.trace_id,
                "timestamp": self.meta.timestamp.isoformat(),
            },
        }
