"""Project application service."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from app.agents.orchestrator import PhaseConflictError
from app.agents.orchestrator import ProjectOrchestrator
from app.core.errors import PhaseConflictAppError
from app.projects.models import Project
from app.projects.models import ProjectPhase
from app.projects.repository import ProjectRepository


class ProjectService:
    """Application operations for projects."""

    def __init__(
        self,
        *,
        repository: ProjectRepository,
        orchestrator: ProjectOrchestrator | None = None,
    ) -> None:
        self._repository = repository
        self._orchestrator = orchestrator or ProjectOrchestrator()

    async def create_project(self, *, owner_uid: str, name: str, idea: str) -> Project:
        project = Project.create(owner_uid=owner_uid, name=name, idea=idea)
        await self._repository.create(project)
        return project

    async def transition_project(self, *, project_id: str, next_phase: ProjectPhase) -> Project:
        project = await self._repository.get(project_id)
        try:
            self._orchestrator.validate_transition(project.phase.value, next_phase.value)
        except PhaseConflictError as exc:
            raise PhaseConflictAppError(project.phase.value, next_phase.value) from exc
        project.update_phase(next_phase)
        await self._repository.update(project)
        return project

    async def get_project_payload(self, project_id: str) -> dict[str, Any]:
        project = await self._repository.get(project_id)
        payload = asdict(project)
        payload["phase"] = project.phase.value
        payload["created_at"] = project.created_at.isoformat()
        payload["updated_at"] = project.updated_at.isoformat()
        return payload
