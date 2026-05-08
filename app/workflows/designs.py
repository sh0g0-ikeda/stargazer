"""Design document generation workflow."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from app.agents.architect import ArchitectAgent
from app.agents.architect import ArchitectGenerator
from app.agents.architect import ARCHITECT_DOCUMENT_TYPES
from app.agents.roles import ARCHITECT_AGENT
from app.agents.runtime import AgentRuntime
from app.agents.schemas import AgentRun
from app.agents.schemas import AgentRunStatus
from app.core.errors import AppError
from app.core.errors import PhaseConflictAppError
from app.core.errors import ValidationAppError
from app.documents.models import Document
from app.documents.models import DocumentType
from app.documents.service import DocumentService
from app.projects.models import ProjectPhase
from app.projects.service import ProjectService


@dataclass(frozen=True)
class DesignWorkflowResult:
    """Result from one design document generation attempt."""

    run: AgentRun
    document: Document | None


class DesignWorkflowService:
    """Generate and persist design documents from the requirements document."""

    def __init__(
        self,
        *,
        project_service: ProjectService,
        document_service: DocumentService,
        agent_runtime: AgentRuntime,
        generator: ArchitectGenerator,
    ) -> None:
        self._project_service = project_service
        self._document_service = document_service
        self._agent_runtime = agent_runtime
        self._generator = generator

    async def generate_design_document(
        self,
        *,
        project_id: str,
        doc_type: DocumentType,
    ) -> DesignWorkflowResult:
        if doc_type not in ARCHITECT_DOCUMENT_TYPES:
            raise ValidationAppError("doc_type is not an architect document", {"doc_type": doc_type.value})

        project_payload = await self._project_service.get_project_payload(project_id)
        project_phase = ProjectPhase(project_payload["phase"])
        if project_phase not in {ProjectPhase.REQUIREMENT_APPROVED, ProjectPhase.DESIGN_DRAFT}:
            raise PhaseConflictAppError(project_phase.value, ProjectPhase.DESIGN_DRAFT.value)

        requirements_document = await self._document_service.latest_document(
            project_id,
            DocumentType.REQUIREMENTS,
        )
        if project_phase is ProjectPhase.REQUIREMENT_APPROVED:
            project = await self._project_service.transition_project(
                project_id=project_id,
                next_phase=ProjectPhase.DESIGN_DRAFT,
            )
            project_phase = project.phase

        input_snapshot = {
            "requirements_doc_md": requirements_document.content_md,
            "doc_type": doc_type.value,
        }
        run = await self._agent_runtime.run_agent(
            project_id=project_id,
            project_phase=project_phase.value,
            role=ARCHITECT_AGENT,
            agent_path="/root/architect_agent",
            agent=ArchitectAgent(self._generator),
            input_snapshot=input_snapshot,
        )
        if run.status is not AgentRunStatus.SUCCEEDED:
            return DesignWorkflowResult(run=run, document=None)

        if run.output is None:
            raise AppError(
                code="AGENT_OUTPUT_MISSING",
                message="architect agent succeeded without output",
                http_status=500,
            )

        document = await self._document_service.create_next_version(
            project_id=project_id,
            doc_type=doc_type,
            content_md=str(run.output["doc_md"]),
            generated_by=run.agent_name,
            prompt_text=_prompt_fingerprint_source(input_snapshot),
            references=(
                f"document:{requirements_document.id}",
                f"agent_run:{run.id}",
                *tuple(run.output.get("references", [])),
            ),
        )
        return DesignWorkflowResult(run=run, document=document)


def _prompt_fingerprint_source(input_snapshot: dict[str, Any]) -> str:
    return json.dumps(input_snapshot, ensure_ascii=False, sort_keys=True)
