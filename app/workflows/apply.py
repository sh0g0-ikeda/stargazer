"""Architecture apply workflow."""

from __future__ import annotations

from dataclasses import dataclass

from app.architectures.service import ArchitectureService
from app.core.errors import PhaseConflictAppError
from app.deployments.cloudbuild import CloudBuildAdapter
from app.deployments.models import BuildStatus
from app.deployments.models import DeploymentRecord
from app.deployments.service import DeploymentService
from app.projects.models import ProjectPhase
from app.projects.service import ProjectService


@dataclass(frozen=True)
class ApplyWorkflowResult:
    """Result from applying one architecture."""

    deployment: DeploymentRecord


class ApplyWorkflowService:
    """Apply the latest approved architecture through Cloud Build."""

    def __init__(
        self,
        *,
        project_service: ProjectService,
        architecture_service: ArchitectureService,
        deployment_service: DeploymentService,
        cloudbuild_adapter: CloudBuildAdapter,
    ) -> None:
        self._project_service = project_service
        self._architecture_service = architecture_service
        self._deployment_service = deployment_service
        self._cloudbuild_adapter = cloudbuild_adapter

    async def apply_latest_architecture(self, *, project_id: str) -> ApplyWorkflowResult:
        project_payload = await self._project_service.get_project_payload(project_id)
        project_phase = ProjectPhase(project_payload["phase"])
        if project_phase is ProjectPhase.ARCHITECTURE_APPROVED:
            await self._project_service.transition_project(
                project_id=project_id,
                next_phase=ProjectPhase.READY_TO_APPLY,
            )
            project_phase = ProjectPhase.READY_TO_APPLY
        if project_phase is not ProjectPhase.READY_TO_APPLY:
            raise PhaseConflictAppError(project_phase.value, ProjectPhase.READY_TO_APPLY.value)

        architecture_payload = await self._architecture_service.latest_payload(project_id)
        await self._project_service.transition_project(
            project_id=project_id,
            next_phase=ProjectPhase.APPLYING,
        )
        build_result = await self._cloudbuild_adapter.trigger_apply(
            architecture_payload=architecture_payload,
        )
        next_phase = (
            ProjectPhase.DEPLOYED
            if build_result.status is BuildStatus.SUCCEEDED
            else ProjectPhase.APPLY_FAILED
        )
        await self._project_service.transition_project(
            project_id=project_id,
            next_phase=next_phase,
        )
        deployment = await self._deployment_service.record_build_result(
            project_id=project_id,
            architecture_id=architecture_payload["id"],
            build_result=build_result,
        )
        return ApplyWorkflowResult(deployment=deployment)
