"""Deployment and build models."""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from enum import Enum
from uuid import uuid4

from app.agents.schemas import utc_now
from app.core.errors import ValidationAppError


class BuildStatus(str, Enum):
    """Cloud Build execution status."""

    SUCCEEDED = "succeeded"
    FAILED = "failed"


@dataclass(frozen=True)
class DeploymentRecord:
    """One architecture apply/deployment result."""

    id: str
    project_id: str
    architecture_id: str
    build_id: str
    status: BuildStatus
    deployed_url: str | None
    logs: tuple[str, ...]
    created_at: datetime = field(default_factory=utc_now)

    @classmethod
    def create(
        cls,
        *,
        project_id: str,
        architecture_id: str,
        build_id: str,
        status: BuildStatus,
        deployed_url: str | None,
        logs: tuple[str, ...],
    ) -> "DeploymentRecord":
        for field_name, value in {
            "project_id": project_id,
            "architecture_id": architecture_id,
            "build_id": build_id,
        }.items():
            if not value.strip():
                raise ValidationAppError(f"{field_name} must not be empty")
        if status is BuildStatus.SUCCEEDED and not deployed_url:
            raise ValidationAppError("deployed_url is required for successful deployments")
        return cls(
            id=str(uuid4()),
            project_id=project_id.strip(),
            architecture_id=architecture_id.strip(),
            build_id=build_id.strip(),
            status=status,
            deployed_url=deployed_url.strip() if deployed_url else None,
            logs=tuple(log.strip() for log in logs if log.strip()),
        )
