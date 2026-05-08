"""Application error types with stable client-facing codes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class AppError(Exception):
    """Base error for expected application failures."""

    code: str
    message: str
    http_status: int
    details: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        Exception.__init__(self, self.message)
        if self.http_status < 400:
            raise ValueError("http_status must be an error status")

    @property
    def safe_details(self) -> dict[str, Any]:
        return dict(self.details or {})


class ValidationAppError(AppError):
    """Invalid user input."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(
            code="VALIDATION_ERROR",
            message=message,
            http_status=422,
            details=details,
        )


class NotFoundAppError(AppError):
    """Requested resource does not exist."""

    def __init__(self, resource_type: str, resource_id: str) -> None:
        super().__init__(
            code="NOT_FOUND",
            message=f"{resource_type} not found",
            http_status=404,
            details={"resource_type": resource_type, "resource_id": resource_id},
        )


class PhaseConflictAppError(AppError):
    """Requested operation is not valid for the current project phase."""

    def __init__(self, current_phase: str, requested_phase: str) -> None:
        super().__init__(
            code="PHASE_CONFLICT",
            message=f"cannot transition from {current_phase} to {requested_phase}",
            http_status=409,
            details={"current_phase": current_phase, "requested_phase": requested_phase},
        )
