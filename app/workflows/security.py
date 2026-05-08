"""Security evaluation workflow."""

from __future__ import annotations

from dataclasses import dataclass

from app.agents.roles import SECURITY_AGENT
from app.agents.runtime import AgentRuntime
from app.agents.schemas import AgentRun
from app.agents.schemas import AgentRunStatus
from app.agents.security import SecurityAgent
from app.agents.security import SecurityEvaluator
from app.architectures.service import ArchitectureService
from app.core.errors import AppError
from app.core.errors import PhaseConflictAppError
from app.projects.models import ProjectPhase
from app.projects.service import ProjectService
from app.security.models import SecurityFinding
from app.security.models import SecuritySeverity
from app.security.service import SecurityFindingService


@dataclass(frozen=True)
class SecurityEvaluationWorkflowResult:
    """Result from one security evaluation pass."""

    run: AgentRun
    findings: list[SecurityFinding]
    critical_count: int


class SecurityEvaluationWorkflowService:
    """Run the mandatory security evaluation loop once."""

    def __init__(
        self,
        *,
        project_service: ProjectService,
        architecture_service: ArchitectureService,
        finding_service: SecurityFindingService,
        agent_runtime: AgentRuntime,
        evaluator: SecurityEvaluator,
    ) -> None:
        self._project_service = project_service
        self._architecture_service = architecture_service
        self._finding_service = finding_service
        self._agent_runtime = agent_runtime
        self._evaluator = evaluator

    async def evaluate_latest_architecture(self, *, project_id: str) -> SecurityEvaluationWorkflowResult:
        project_payload = await self._project_service.get_project_payload(project_id)
        project_phase = ProjectPhase(project_payload["phase"])
        if project_phase not in {ProjectPhase.ARCHITECTURE_DRAFT, ProjectPhase.SECURITY_REVIEW}:
            raise PhaseConflictAppError(project_phase.value, ProjectPhase.SECURITY_REVIEW.value)

        architecture_payload = await self._architecture_service.latest_payload(project_id)
        if project_phase is ProjectPhase.ARCHITECTURE_DRAFT:
            project = await self._project_service.transition_project(
                project_id=project_id,
                next_phase=ProjectPhase.SECURITY_REVIEW,
            )
            project_phase = project.phase

        run = await self._agent_runtime.run_agent(
            project_id=project_id,
            project_phase=project_phase.value,
            role=SECURITY_AGENT,
            agent_path="/root/security_agent",
            agent=SecurityAgent(self._evaluator),
            input_snapshot={
                "target_type": "architecture",
                "target_id": architecture_payload["id"],
                "architecture_spec": architecture_payload["spec"],
            },
        )
        if run.status is not AgentRunStatus.SUCCEEDED:
            return SecurityEvaluationWorkflowResult(run=run, findings=[], critical_count=0)

        if run.output is None:
            raise AppError(
                code="AGENT_OUTPUT_MISSING",
                message="security agent succeeded without output",
                http_status=500,
            )

        findings = await self._finding_service.create_findings(
            project_id=project_id,
            target_type="architecture",
            target_id=architecture_payload["id"],
            finding_payloads=list(run.output["findings"]),
        )
        critical_count = sum(1 for finding in findings if finding.severity is SecuritySeverity.CRITICAL)
        return SecurityEvaluationWorkflowResult(
            run=run,
            findings=findings,
            critical_count=critical_count,
        )
