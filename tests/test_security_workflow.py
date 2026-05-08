import unittest
from typing import Any

from app.agents.runtime import AgentRuntime
from app.agents.runtime import InMemoryAgentStore
from app.agents.security import SecurityEvaluationRequest
from app.agents.tool_guard import DEFAULT_TOOL_DEFINITIONS
from app.agents.tool_guard import ToolGuard
from app.architectures.repository import InMemoryArchitectureRepository
from app.architectures.service import ArchitectureService
from app.core.errors import PhaseConflictAppError
from app.projects.models import ProjectPhase
from app.projects.repository import InMemoryProjectRepository
from app.projects.service import ProjectService
from app.security.repository import InMemorySecurityFindingRepository
from app.security.service import SecurityFindingService
from app.workflows.security import SecurityEvaluationWorkflowService


def valid_spec() -> dict:
    return {
        "project_id": "gcp-project",
        "region": "asia-northeast1",
        "nodes": [
            {
                "id": "backend",
                "type": "cloud_run",
                "name": "Backend",
                "parameters": {},
                "rationale": "APIを公開する",
                "cost_band": "low",
            }
        ],
        "edges": [],
    }


class StaticWorkflowSecurityEvaluator:
    def __init__(self, output: Any) -> None:
        self.output = output
        self.requests: list[SecurityEvaluationRequest] = []

    async def evaluate(self, request: SecurityEvaluationRequest) -> Any:
        self.requests.append(request)
        return dict(self.output)


async def make_workflow(
    output: Any,
) -> tuple[ProjectService, InMemoryProjectRepository, ArchitectureService, SecurityFindingService, SecurityEvaluationWorkflowService]:
    project_repository = InMemoryProjectRepository()
    project_service = ProjectService(repository=project_repository)
    architecture_service = ArchitectureService(InMemoryArchitectureRepository())
    finding_service = SecurityFindingService(InMemorySecurityFindingRepository())
    workflow = SecurityEvaluationWorkflowService(
        project_service=project_service,
        architecture_service=architecture_service,
        finding_service=finding_service,
        agent_runtime=AgentRuntime(
            store=InMemoryAgentStore(),
            tool_guard=ToolGuard(DEFAULT_TOOL_DEFINITIONS),
        ),
        evaluator=StaticWorkflowSecurityEvaluator(output),
    )
    return project_service, project_repository, architecture_service, finding_service, workflow


class SecurityEvaluationWorkflowServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_evaluate_latest_architecture_saves_findings_and_counts_critical(self) -> None:
        project_service, project_repository, architecture_service, finding_service, workflow = await make_workflow(
            {
                "findings": [
                    {
                        "severity": "critical",
                        "category": "iam",
                        "message": "権限が広すぎる",
                        "suggestion": "最小権限にする",
                    },
                    {
                        "severity": "info",
                        "category": "logging",
                        "message": "ログ設計あり",
                        "suggestion": "継続する",
                    },
                ]
            }
        )
        project = await project_service.create_project(
            owner_uid="user-1",
            name="Support Desk",
            idea="問い合わせ管理アプリ",
        )
        project.update_phase(ProjectPhase.ARCHITECTURE_DRAFT)
        await project_repository.update(project)
        proposal = await architecture_service.create_next_proposal(
            project_id=project.id,
            spec_payload=valid_spec(),
            rationale_md="採用理由",
            cloudbuild_yaml="steps: []",
            gcloud_commands=("gcloud run services list",),
        )

        result = await workflow.evaluate_latest_architecture(project_id=project.id)
        findings = await finding_service.list_by_target(project.id, "architecture", proposal.id)
        updated_project = await project_repository.get(project.id)

        self.assertEqual(result.critical_count, 1)
        self.assertEqual(len(findings), 2)
        self.assertEqual(updated_project.phase, ProjectPhase.SECURITY_REVIEW)

    async def test_evaluate_latest_architecture_rejects_wrong_phase(self) -> None:
        project_service, project_repository, architecture_service, _, workflow = await make_workflow(
            {"findings": []}
        )
        project = await project_service.create_project(
            owner_uid="user-1",
            name="Support Desk",
            idea="問い合わせ管理アプリ",
        )
        project.update_phase(ProjectPhase.DEPLOYED)
        await project_repository.update(project)
        await architecture_service.create_next_proposal(
            project_id=project.id,
            spec_payload=valid_spec(),
            rationale_md="採用理由",
            cloudbuild_yaml="steps: []",
            gcloud_commands=("gcloud run services list",),
        )

        with self.assertRaises(PhaseConflictAppError):
            await workflow.evaluate_latest_architecture(project_id=project.id)


if __name__ == "__main__":
    unittest.main()
