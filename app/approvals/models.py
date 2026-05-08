"""Approval domain models."""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from app.agents.schemas import utc_now
from app.core.errors import ValidationAppError


class ApprovalGate(str, Enum):
    """Human approval gate names in the MVP workflow."""

    REQUIREMENTS = "requirements"
    DESIGN = "design"
    ARCHITECTURE = "architecture"
    TARGET_APP = "target_app"


class ApprovalDecision(str, Enum):
    """Supported approval decisions."""

    APPROVED = "approved"
    REVISION_REQUESTED = "revision_requested"


@dataclass(frozen=True)
class ApprovalRecord:
    """Immutable record of one approval decision."""

    id: str
    project_id: str
    gate: ApprovalGate
    decision: ApprovalDecision
    decided_by: str
    rationale: str
    snapshot: dict[str, Any]
    created_at: datetime = field(default_factory=utc_now)

    @classmethod
    def create(
        cls,
        *,
        project_id: str,
        gate: ApprovalGate,
        decision: ApprovalDecision,
        decided_by: str,
        rationale: str,
        snapshot: dict[str, Any] | None = None,
    ) -> "ApprovalRecord":
        if not project_id.strip():
            raise ValidationAppError("project_id must not be empty")
        if not decided_by.strip():
            raise ValidationAppError("decided_by must not be empty")
        if len(rationale.strip()) > 2_000:
            raise ValidationAppError("approval rationale must be 2000 characters or fewer")
        return cls(
            id=str(uuid4()),
            project_id=project_id.strip(),
            gate=gate,
            decision=decision,
            decided_by=decided_by.strip(),
            rationale=rationale.strip(),
            snapshot=dict(snapshot or {}),
        )
