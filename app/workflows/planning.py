"""GCP planning workflow."""

from __future__ import annotations

from dataclasses import dataclass

from app.agents.gcp_planner import GcpPlannerAgent
from app.agents.gcp_planner import GcpPlannerGenerator
from app.agents.roles import GCP_PLANNER_AGENT
from app.agents.runtime import AgentRuntime
from app.agents.schemas import AgentRun
from app.agents.schemas import AgentRunStatus
from app.architectures.models import ArchitectureProposal
from app.architectures.service import ArchitectureService
from app.core.errors import AppError
from app.core.errors import PhaseConflictAppError
from app.documents.models import DocumentType
from app.documents.service import DocumentService
from app.projects.models import ProjectPhase
from app.projects.service import ProjectService


@dataclass(frozen=True)
class PlanningWorkflowResult:
    """Result from one GCP planning attempt."""

    run: AgentRun
    proposal: ArchitectureProposal | None


class PlanningWorkflowService:
    """Generate and persist a GCP architecture proposal."""

    def __init__(
        self,
        *,
        project_service: ProjectService,
        document_service: DocumentService,
        architecture_service: ArchitectureService,
        agent_runtime: AgentRuntime,
        generator: GcpPlannerGenerator,
    ) -> None:
        self._project_service = project_service
        self._document_service = document_service
        self._architecture_service = architecture_service
        self._agent_runtime = agent_runtime
        self._generator = generator

    async def propose_architecture(
        self,
        *,
        project_id: str,
        target_project_id: str,
    ) -> PlanningWorkflowResult:
        project_payload = await self._project_service.get_project_payload(project_id)
        project_phase = ProjectPhase(project_payload["phase"])
        if project_phase is ProjectPhase.DESIGN_APPROVED:
            project = await self._project_service.transition_project(
                project_id=project_id,
                next_phase=ProjectPhase.ARCHITECTURE_DRAFT,
            )
            project_phase = project.phase
        elif project_phase is not ProjectPhase.ARCHITECTURE_DRAFT:
            raise PhaseConflictAppError(project_phase.value, ProjectPhase.ARCHITECTURE_DRAFT.value)

        requirements_document = await self._document_service.latest_document(
            project_id,
            DocumentType.REQUIREMENTS,
        )
        basic_design_document = await self._document_service.latest_document(
            project_id,
            DocumentType.BASIC_DESIGN,
        )
        input_snapshot = {
            "requirements_doc_md": requirements_document.content_md,
            "basic_design_md": basic_design_document.content_md,
            "target_project_id": target_project_id,
        }
        run = await self._agent_runtime.run_agent(
            project_id=project_id,
            project_phase=project_phase.value,
            role=GCP_PLANNER_AGENT,
            agent_path="/root/gcp_planner_agent",
            agent=GcpPlannerAgent(self._generator),
            input_snapshot=input_snapshot,
        )
        if run.status is not AgentRunStatus.SUCCEEDED:
            return PlanningWorkflowResult(run=run, proposal=None)

        if run.output is None:
            raise AppError(
                code="AGENT_OUTPUT_MISSING",
                message="gcp planner agent succeeded without output",
                http_status=500,
            )

        proposal = await self._architecture_service.create_next_proposal(
            project_id=project_id,
            spec_payload=run.output["architecture_spec"],
            rationale_md=str(run.output["rationale_md"]),
            cloudbuild_yaml=str(run.output["cloudbuild_yaml"]),
            gcloud_commands=tuple(run.output["gcloud_commands"]),
        )
        return PlanningWorkflowResult(run=run, proposal=proposal)
