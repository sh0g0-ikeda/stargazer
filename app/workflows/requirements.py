"""Requirement generation workflow."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from app.agents.requirement import RequirementAgent
from app.agents.requirement import RequirementGenerator
from app.agents.roles import REQUIREMENT_AGENT
from app.agents.runtime import AgentRuntime
from app.agents.schemas import AgentRun
from app.agents.schemas import AgentRunStatus
from app.core.errors import AppError
from app.core.errors import PhaseConflictAppError
from app.documents.models import Document
from app.documents.models import DocumentType
from app.documents.service import DocumentService
from app.projects.models import ProjectPhase
from app.projects.service import ProjectService


@dataclass(frozen=True)
class RequirementWorkflowResult:
    """Result from one requirement generation attempt."""

    run: AgentRun
    document: Document | None


class RequirementWorkflowService:
    """Generate and persist a requirements document for a project."""

    def __init__(
        self,
        *,
        project_service: ProjectService,
        document_service: DocumentService,
        agent_runtime: AgentRuntime,
        generator: RequirementGenerator,
    ) -> None:
        self._project_service = project_service
        self._document_service = document_service
        self._agent_runtime = agent_runtime
        self._generator = generator

    async def generate_requirements(
        self,
        *,
        project_id: str,
        form_responses: dict[str, Any] | None = None,
        follow_up_answers: dict[str, str] | None = None,
    ) -> RequirementWorkflowResult:
        project_payload = await self._project_service.get_project_payload(project_id)
        project_phase = ProjectPhase(project_payload["phase"])
        if project_phase is ProjectPhase.DRAFT:
            project = await self._project_service.transition_project(
                project_id=project_id,
                next_phase=ProjectPhase.REQUIREMENT_DRAFT,
            )
            project_phase = project.phase
        elif project_phase not in {
            ProjectPhase.REQUIREMENT_DRAFT,
            ProjectPhase.DESIGN_DRAFT,
        }:
            raise PhaseConflictAppError(project_phase.value, ProjectPhase.REQUIREMENT_DRAFT.value)

        input_snapshot = {
            "idea": project_payload["idea"],
            "form_responses": form_responses or {},
            "follow_up_answers": follow_up_answers or {},
        }
        run = await self._agent_runtime.run_agent(
            project_id=project_id,
            project_phase=project_phase.value,
            role=REQUIREMENT_AGENT,
            agent_path="/root/requirement_agent",
            agent=RequirementAgent(self._generator),
            input_snapshot=input_snapshot,
        )
        if run.status is not AgentRunStatus.SUCCEEDED:
            return RequirementWorkflowResult(run=run, document=None)

        if run.output is None:
            raise AppError(
                code="AGENT_OUTPUT_MISSING",
                message="requirement agent succeeded without output",
                http_status=500,
            )

        document = await self._document_service.create_next_version(
            project_id=project_id,
            doc_type=DocumentType.REQUIREMENTS,
            content_md=str(run.output["requirements_doc_md"]),
            generated_by=run.agent_name,
            prompt_text=_prompt_fingerprint_source(input_snapshot),
            references=(f"project:{project_id}", f"agent_run:{run.id}"),
        )
        return RequirementWorkflowResult(run=run, document=document)


def _prompt_fingerprint_source(input_snapshot: dict[str, Any]) -> str:
    return json.dumps(input_snapshot, ensure_ascii=False, sort_keys=True)
