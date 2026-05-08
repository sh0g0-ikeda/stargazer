"""Typed schemas shared by the agent runtime components."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal
from uuid import uuid4


def utc_now() -> datetime:
    """Return a timezone-aware timestamp for persisted runtime records."""

    return datetime.now(timezone.utc)


class AgentRunStatus(str, Enum):
    """Lifecycle status derived from agent events."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    WAITING_APPROVAL = "WAITING_APPROVAL"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class AgentEventType(str, Enum):
    """Event types emitted by the runtime."""

    RUN_CREATED = "RUN_CREATED"
    RUN_STARTED = "RUN_STARTED"
    PROGRESS = "PROGRESS"
    TOOL_REQUESTED = "TOOL_REQUESTED"
    TOOL_FINISHED = "TOOL_FINISHED"
    APPROVAL_REQUIRED = "APPROVAL_REQUIRED"
    RUN_SUCCEEDED = "RUN_SUCCEEDED"
    RUN_FAILED = "RUN_FAILED"
    RUN_CANCELLED = "RUN_CANCELLED"


FINAL_EVENT_STATUS = {
    AgentEventType.RUN_SUCCEEDED: AgentRunStatus.SUCCEEDED,
    AgentEventType.RUN_FAILED: AgentRunStatus.FAILED,
    AgentEventType.RUN_CANCELLED: AgentRunStatus.CANCELLED,
}


class ToolRisk(str, Enum):
    """Risk level for tools exposed to agents."""

    READ_ONLY = "READ_ONLY"
    WRITE = "WRITE"
    DESTRUCTIVE = "DESTRUCTIVE"


@dataclass(frozen=True)
class ProgressUpdate:
    """A monotonic user-visible progress update."""

    percent: int
    label: str

    def __post_init__(self) -> None:
        if self.percent < 0 or self.percent > 100:
            raise ValueError("progress percent must be between 0 and 100")
        if not self.label.strip():
            raise ValueError("progress label must not be empty")


@dataclass(frozen=True)
class AgentRole:
    """Static role configuration for an agent."""

    name: str
    model: str
    thinking_level: Literal["minimal", "low", "medium", "high"]
    allowed_tools: frozenset[str] = field(default_factory=frozenset)
    timeout_seconds: int = 120
    max_attempts: int = 1

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("agent role name must not be empty")
        if not self.model:
            raise ValueError("agent role model must not be empty")
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        if self.max_attempts <= 0:
            raise ValueError("max_attempts must be positive")


@dataclass(frozen=True)
class ToolDefinition:
    """Policy metadata for a callable tool."""

    name: str
    risk: ToolRisk
    allowed_phases: frozenset[str]
    requires_approval: bool = False

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("tool name must not be empty")
        if not self.allowed_phases:
            raise ValueError("tool must allow at least one project phase")


@dataclass(frozen=True)
class ToolRequest:
    """A validated tool request from an agent."""

    tool_name: str
    arguments: dict[str, Any]

    def __post_init__(self) -> None:
        if not self.tool_name:
            raise ValueError("tool_name must not be empty")


@dataclass(frozen=True)
class ToolDecision:
    """Decision returned by ToolGuard."""

    allowed: bool
    code: str
    message: str
    requires_approval: bool = False


@dataclass
class AgentRun:
    """Persisted runtime state for one agent execution."""

    id: str
    project_id: str
    agent_name: str
    agent_path: str
    model: str
    thinking_level: str
    input_snapshot: dict[str, Any]
    status: AgentRunStatus = AgentRunStatus.PENDING
    progress_percent: int = 0
    progress_label: str = "created"
    parent_run_id: str | None = None
    output: dict[str, Any] | None = None
    error_code: str | None = None
    error_message: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    created_at: datetime = field(default_factory=utc_now)

    @classmethod
    def create(
        cls,
        *,
        project_id: str,
        role: AgentRole,
        agent_path: str,
        input_snapshot: dict[str, Any],
        parent_run_id: str | None = None,
    ) -> "AgentRun":
        return cls(
            id=str(uuid4()),
            project_id=project_id,
            agent_name=role.name,
            agent_path=agent_path,
            model=role.model,
            thinking_level=role.thinking_level,
            input_snapshot=dict(input_snapshot),
            parent_run_id=parent_run_id,
        )


@dataclass(frozen=True)
class AgentEvent:
    """Ordered event emitted during an agent run."""

    id: str
    run_id: str
    agent_path: str
    seq: int
    event_type: AgentEventType
    payload: dict[str, Any]
    occurred_at: datetime = field(default_factory=utc_now)

    @classmethod
    def create(
        cls,
        *,
        run_id: str,
        agent_path: str,
        seq: int,
        event_type: AgentEventType,
        payload: dict[str, Any] | None = None,
    ) -> "AgentEvent":
        if seq <= 0:
            raise ValueError("event seq must be positive")
        return cls(
            id=str(uuid4()),
            run_id=run_id,
            agent_path=agent_path,
            seq=seq,
            event_type=event_type,
            payload=payload or {},
        )


def derive_status_from_events(events: list[AgentEvent]) -> AgentRunStatus:
    """Derive the latest run status from ordered runtime events."""

    status = AgentRunStatus.PENDING
    for event in sorted(events, key=lambda item: item.seq):
        if event.event_type is AgentEventType.RUN_STARTED:
            status = AgentRunStatus.RUNNING
        elif event.event_type is AgentEventType.APPROVAL_REQUIRED:
            status = AgentRunStatus.WAITING_APPROVAL
        elif event.event_type in FINAL_EVENT_STATUS:
            status = FINAL_EVENT_STATUS[event.event_type]
    return status
