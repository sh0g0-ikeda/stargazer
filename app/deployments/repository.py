"""Deployment persistence boundary."""

from __future__ import annotations

from typing import Protocol

from app.core.errors import NotFoundAppError
from app.deployments.models import DeploymentRecord


class DeploymentRepository(Protocol):
    """Storage boundary for deployment records."""

    async def create(self, deployment: DeploymentRecord) -> None:
        """Persist a deployment record."""

    async def latest(self, project_id: str) -> DeploymentRecord:
        """Return the latest deployment for one project."""

    async def list_by_project(self, project_id: str) -> list[DeploymentRecord]:
        """Return deployment history for one project."""


class InMemoryDeploymentRepository:
    """Local deployment repository used by tests and demo mode."""

    def __init__(self) -> None:
        self._deployments: list[DeploymentRecord] = []

    async def create(self, deployment: DeploymentRecord) -> None:
        self._deployments.append(deployment)

    async def latest(self, project_id: str) -> DeploymentRecord:
        deployments = await self.list_by_project(project_id)
        if not deployments:
            raise NotFoundAppError("deployment", project_id)
        return deployments[-1]

    async def list_by_project(self, project_id: str) -> list[DeploymentRecord]:
        return [
            deployment
            for deployment in sorted(self._deployments, key=lambda item: item.created_at)
            if deployment.project_id == project_id
        ]
