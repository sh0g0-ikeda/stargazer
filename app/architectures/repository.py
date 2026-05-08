"""Architecture proposal persistence boundary."""

from __future__ import annotations

from typing import Protocol

from app.architectures.models import ArchitectureProposal
from app.core.errors import NotFoundAppError


class ArchitectureRepository(Protocol):
    """Storage boundary for architecture proposals."""

    async def create(self, proposal: ArchitectureProposal) -> None:
        """Persist an architecture proposal."""

    async def latest(self, project_id: str) -> ArchitectureProposal:
        """Return the latest proposal for a project."""

    async def list_by_project(self, project_id: str) -> list[ArchitectureProposal]:
        """Return all proposals for a project."""


class InMemoryArchitectureRepository:
    """Local architecture repository used by tests and early development."""

    def __init__(self) -> None:
        self._proposals: dict[str, list[ArchitectureProposal]] = {}

    async def create(self, proposal: ArchitectureProposal) -> None:
        proposals = self._proposals.setdefault(proposal.project_id, [])
        if any(existing.version == proposal.version for existing in proposals):
            raise ValueError(f"architecture version already exists: v{proposal.version}")
        proposals.append(proposal)
        proposals.sort(key=lambda item: item.version)

    async def latest(self, project_id: str) -> ArchitectureProposal:
        proposals = await self.list_by_project(project_id)
        if not proposals:
            raise NotFoundAppError("architecture", project_id)
        return proposals[-1]

    async def list_by_project(self, project_id: str) -> list[ArchitectureProposal]:
        return list(self._proposals.get(project_id, []))
