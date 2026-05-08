"""Timeline persistence boundary."""

from __future__ import annotations

from typing import Protocol

from app.timeline.models import TimelineEvent


class TimelineRepository(Protocol):
    """Storage boundary for timeline events."""

    async def create(self, event: TimelineEvent) -> None:
        """Persist a timeline event."""

    async def list_by_project(self, project_id: str) -> list[TimelineEvent]:
        """Return timeline events for one project."""


class InMemoryTimelineRepository:
    """Local timeline repository used by tests and early development."""

    def __init__(self) -> None:
        self._events: list[TimelineEvent] = []

    async def create(self, event: TimelineEvent) -> None:
        self._events.append(event)

    async def list_by_project(self, project_id: str) -> list[TimelineEvent]:
        return sorted(
            (event for event in self._events if event.project_id == project_id),
            key=lambda event: event.occurred_at,
        )
