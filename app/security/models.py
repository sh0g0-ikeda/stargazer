"""Security finding models."""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from enum import Enum
from uuid import uuid4

from app.agents.schemas import utc_now
from app.core.errors import ValidationAppError


class SecuritySeverity(str, Enum):
    """Severity for security findings."""

    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


@dataclass(frozen=True)
class SecurityFinding:
    """One validated security finding."""

    id: str
    project_id: str
    target_type: str
    target_id: str
    severity: SecuritySeverity
    category: str
    message: str
    suggestion: str
    created_at: datetime = field(default_factory=utc_now)

    @classmethod
    def create(
        cls,
        *,
        project_id: str,
        target_type: str,
        target_id: str,
        severity: SecuritySeverity,
        category: str,
        message: str,
        suggestion: str,
    ) -> "SecurityFinding":
        for field_name, value in {
            "project_id": project_id,
            "target_type": target_type,
            "target_id": target_id,
            "category": category,
            "message": message,
            "suggestion": suggestion,
        }.items():
            if not value.strip():
                raise ValidationAppError(f"{field_name} must not be empty")
        return cls(
            id=str(uuid4()),
            project_id=project_id.strip(),
            target_type=target_type.strip(),
            target_id=target_id.strip(),
            severity=severity,
            category=category.strip(),
            message=message.strip(),
            suggestion=suggestion.strip(),
        )
