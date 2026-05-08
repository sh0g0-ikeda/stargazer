"""Deployment application service."""

from __future__ import annotations

from typing import Any

from app.deployments.cloudbuild import BuildResult
from app.deployments.models import DeploymentRecord
from app.deployments.repository import DeploymentRepository


class DeploymentService:
    """Create and read deployment records."""

    def __init__(self, repository: DeploymentRepository) -> None:
        self._repository = repository

    async def record_build_result(
        self,
        *,
        project_id: str,
        architecture_id: str,
        build_result: BuildResult,
    ) -> DeploymentRecord:
        deployment = DeploymentRecord.create(
            project_id=project_id,
            architecture_id=architecture_id,
            build_id=build_result.build_id,
            status=build_result.status,
            deployed_url=build_result.deployed_url,
            logs=build_result.logs,
        )
        await self._repository.create(deployment)
        return deployment

    async def latest_payload(self, project_id: str) -> dict[str, Any]:
        deployment = await self._repository.latest(project_id)
        return {
            "id": deployment.id,
            "project_id": deployment.project_id,
            "architecture_id": deployment.architecture_id,
            "build_id": deployment.build_id,
            "status": deployment.status.value,
            "deployed_url": deployment.deployed_url,
            "logs": list(deployment.logs),
            "created_at": deployment.created_at.isoformat(),
        }
