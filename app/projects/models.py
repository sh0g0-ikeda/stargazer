"""Project domain models."""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from enum import Enum
from uuid import uuid4

from app.agents.schemas import utc_now
from app.core.errors import ValidationAppError


class ProjectPhase(str, Enum):
    """Top-level project workflow phases."""

    DRAFT = "DRAFT"
    REQUIREMENT_DRAFT = "REQUIREMENT_DRAFT"
    REQUIREMENT_APPROVED = "REQUIREMENT_APPROVED"
    DESIGN_DRAFT = "DESIGN_DRAFT"
    DESIGN_APPROVED = "DESIGN_APPROVED"
    ARCHITECTURE_DRAFT = "ARCHITECTURE_DRAFT"
    SECURITY_REVIEW = "SECURITY_REVIEW"
    ARCHITECTURE_APPROVED = "ARCHITECTURE_APPROVED"
    READY_TO_APPLY = "READY_TO_APPLY"
    APPLYING = "APPLYING"
    APPLY_FAILED = "APPLY_FAILED"
    DEPLOYED = "DEPLOYED"


@dataclass
class Project:
    """User project tracked by Star Gazer."""

    id: str
    owner_uid: str
    name: str
    idea: str
    phase: ProjectPhase = ProjectPhase.DRAFT
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)

    @classmethod
    def create(cls, *, owner_uid: str, name: str, idea: str) -> "Project":
        validate_project_input(owner_uid=owner_uid, name=name, idea=idea)
        return cls(id=str(uuid4()), owner_uid=owner_uid, name=name.strip(), idea=idea.strip())

    def rename(self, name: str) -> None:
        validate_project_name(name)
        self.name = name.strip()
        self.updated_at = utc_now()

    def update_phase(self, phase: ProjectPhase) -> None:
        self.phase = phase
        self.updated_at = utc_now()


def validate_project_input(*, owner_uid: str, name: str, idea: str) -> None:
    if not owner_uid.strip():
        raise ValidationAppError("owner_uid must not be empty")
    validate_project_name(name)
    if not idea.strip():
        raise ValidationAppError("idea must not be empty")
    if len(idea.strip()) > 10_000:
        raise ValidationAppError("idea must be 10000 characters or fewer")


def validate_project_name(name: str) -> None:
    if not name.strip():
        raise ValidationAppError("project name must not be empty")
    if len(name.strip()) > 120:
        raise ValidationAppError("project name must be 120 characters or fewer")
