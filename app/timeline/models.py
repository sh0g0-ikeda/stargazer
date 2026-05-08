"""Timeline event models."""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from app.agents.schemas import utc_now
from app.core.errors import ValidationAppError


class TimelineCategory(str, Enum):
    """User-facing timeline event category."""

    USER_ACTION = "user_action"
    AGENT_ACTION = "agent_action"
    SYSTEM_EVENT = "system_event"
    APPROVAL = "approval"
    ERROR = "error"


class TimelineResult(str, Enum):
    """Result state for a timeline event."""

    SUCCESS = "success"
    FAILURE = "failure"
    IN_PROGRESS = "in_progress"


@dataclass(frozen=True)
class TimelineEvent:
    """User-facing project timeline event."""

    id: str
    project_id: str
    category: TimelineCategory
    action: str
    result: TimelineResult
    occurred_at: datetime = field(default_factory=utc_now)
    agent_name: str | None = None
    target: dict[str, str] | None = None
    rationale_md: str | None = None
    duration_ms: int | None = None
    links: tuple[dict[str, str], ...] = field(default_factory=tuple)
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        *,
        project_id: str,
        category: TimelineCategory,
        action: str,
        result: TimelineResult,
        agent_name: str | None = None,
        target: dict[str, str] | None = None,
        rationale_md: str | None = None,
        duration_ms: int | None = None,
        links: tuple[dict[str, str], ...] = (),
        metadata: dict[str, Any] | None = None,
    ) -> "TimelineEvent":
        if not project_id.strip():
            raise ValidationAppError("project_id must not be empty")
        if not action.strip():
            raise ValidationAppError("timeline action must not be empty")
        if duration_ms is not None and duration_ms < 0:
            raise ValidationAppError("duration_ms must not be negative")
        _validate_target(target)
        _validate_links(links)
        return cls(
            id=str(uuid4()),
            project_id=project_id.strip(),
            category=category,
            action=action.strip(),
            result=result,
            agent_name=agent_name.strip() if agent_name else None,
            target=dict(target) if target else None,
            rationale_md=rationale_md.strip() if rationale_md else None,
            duration_ms=duration_ms,
            links=tuple(dict(link) for link in links),
            metadata=dict(metadata or {}),
        )


def _validate_target(target: dict[str, str] | None) -> None:
    if target is None:
        return
    if not target.get("type") or not target.get("id"):
        raise ValidationAppError("timeline target must include type and id")


def _validate_links(links: tuple[dict[str, str], ...]) -> None:
    for link in links:
        if not link.get("name") or not link.get("url"):
            raise ValidationAppError("timeline links must include name and url")
