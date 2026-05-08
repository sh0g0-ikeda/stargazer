"""Framework-independent API facade.

FastAPI handlers can delegate to this facade without embedding workflow logic
inside transport code.
"""

from __future__ import annotations

from app.api.responses import ApiResponse
from app.core.errors import AppError
from app.core.errors import ValidationAppError
from app.documents.models import DocumentType
from app.projects.models import ProjectPhase
from app.projects.service import ProjectService
from app.workflows.designs import DesignWorkflowService
from app.workflows.planning import PlanningWorkflowService
from app.workflows.requirements import RequirementWorkflowService
from app.workflows.security import SecurityEvaluationWorkflowService


class StarGazerApiFacade:
    """Application-facing operations exposed by the backend API."""

    def __init__(
        self,
        *,
        project_service: ProjectService,
        requirement_workflow: RequirementWorkflowService,
        design_workflow: DesignWorkflowService,
        planning_workflow: PlanningWorkflowService,
        security_workflow: SecurityEvaluationWorkflowService,
    ) -> None:
        self._project_service = project_service
        self._requirement_workflow = requirement_workflow
        self._design_workflow = design_workflow
        self._planning_workflow = planning_workflow
        self._security_workflow = security_workflow

    async def create_project(
        self,
        *,
        owner_uid: str,
        name: str,
        idea: str,
        request_id: str | None = None,
    ) -> ApiResponse:
        try:
            project = await self._project_service.create_project(
                owner_uid=owner_uid,
                name=name,
                idea=idea,
            )
        except AppError as exc:
            return ApiResponse.failed(exc, request_id=request_id)
        return ApiResponse.ok(
            {
                "id": project.id,
                "owner_uid": project.owner_uid,
                "name": project.name,
                "idea": project.idea,
                "phase": project.phase.value,
            },
            request_id=request_id,
        )

    async def get_project(self, *, project_id: str, request_id: str | None = None) -> ApiResponse:
        try:
            payload = await self._project_service.get_project_payload(project_id)
        except AppError as exc:
            return ApiResponse.failed(exc, request_id=request_id)
        return ApiResponse.ok(payload, request_id=request_id)

    async def transition_project(
        self,
        *,
        project_id: str,
        next_phase: str,
        request_id: str | None = None,
    ) -> ApiResponse:
        try:
            parsed_next_phase = ProjectPhase(next_phase)
            project = await self._project_service.transition_project(
                project_id=project_id,
                next_phase=parsed_next_phase,
            )
        except ValueError:
            error = ValidationAppError("next_phase is not supported", {"next_phase": next_phase})
            return ApiResponse.failed(error, request_id=request_id)
        except AppError as exc:
            return ApiResponse.failed(exc, request_id=request_id)
        return ApiResponse.ok(
            {
                "id": project.id,
                "phase": project.phase.value,
            },
            request_id=request_id,
        )

    async def generate_requirements(
        self,
        *,
        project_id: str,
        request_id: str | None = None,
    ) -> ApiResponse:
        try:
            result = await self._requirement_workflow.generate_requirements(project_id=project_id)
        except AppError as exc:
            return ApiResponse.failed(exc, request_id=request_id)
        return ApiResponse.ok(
            {
                "run_id": result.run.id,
                "run_status": result.run.status.value,
                "document_id": result.document.id if result.document else None,
            },
            request_id=request_id,
        )

    async def generate_basic_design(
        self,
        *,
        project_id: str,
        request_id: str | None = None,
    ) -> ApiResponse:
        try:
            result = await self._design_workflow.generate_design_document(
                project_id=project_id,
                doc_type=DocumentType.BASIC_DESIGN,
            )
        except AppError as exc:
            return ApiResponse.failed(exc, request_id=request_id)
        return ApiResponse.ok(
            {
                "run_id": result.run.id,
                "run_status": result.run.status.value,
                "document_id": result.document.id if result.document else None,
            },
            request_id=request_id,
        )

    async def propose_architecture(
        self,
        *,
        project_id: str,
        target_project_id: str,
        request_id: str | None = None,
    ) -> ApiResponse:
        try:
            result = await self._planning_workflow.propose_architecture(
                project_id=project_id,
                target_project_id=target_project_id,
            )
        except AppError as exc:
            return ApiResponse.failed(exc, request_id=request_id)
        return ApiResponse.ok(
            {
                "run_id": result.run.id,
                "run_status": result.run.status.value,
                "architecture_id": result.proposal.id if result.proposal else None,
            },
            request_id=request_id,
        )

    async def evaluate_security(
        self,
        *,
        project_id: str,
        request_id: str | None = None,
    ) -> ApiResponse:
        try:
            result = await self._security_workflow.evaluate_latest_architecture(project_id=project_id)
        except AppError as exc:
            return ApiResponse.failed(exc, request_id=request_id)
        return ApiResponse.ok(
            {
                "run_id": result.run.id,
                "run_status": result.run.status.value,
                "findings": len(result.findings),
                "critical_count": result.critical_count,
            },
            request_id=request_id,
        )
