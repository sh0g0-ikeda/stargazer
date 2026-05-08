"""Code generation models."""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from uuid import uuid4

from app.agents.schemas import utc_now
from app.core.errors import ValidationAppError


@dataclass(frozen=True)
class GeneratedFile:
    """One generated target application file."""

    path: str
    content: str

    def __post_init__(self) -> None:
        if not self.path.strip():
            raise ValidationAppError("generated file path must not be empty")
        if self.path.startswith("/") or ".." in self.path.split("/"):
            raise ValidationAppError("generated file path must be relative and safe")
        if not self.content.strip():
            raise ValidationAppError("generated file content must not be empty")


@dataclass(frozen=True)
class CodeGenerationResult:
    """Generated target application package."""

    id: str
    project_id: str
    app_name: str
    files: tuple[GeneratedFile, ...]
    notes_md: str
    created_at: datetime = field(default_factory=utc_now)

    @classmethod
    def create(
        cls,
        *,
        project_id: str,
        app_name: str,
        files: tuple[GeneratedFile, ...],
        notes_md: str,
    ) -> "CodeGenerationResult":
        if not project_id.strip():
            raise ValidationAppError("project_id must not be empty")
        if not app_name.strip():
            raise ValidationAppError("app_name must not be empty")
        if not files:
            raise ValidationAppError("generated files must not be empty")
        return cls(
            id=str(uuid4()),
            project_id=project_id.strip(),
            app_name=app_name.strip(),
            files=files,
            notes_md=notes_md.strip(),
        )
