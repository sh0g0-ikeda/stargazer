import unittest
from typing import Any

from app.agents.gcp_planner import GcpPlannerRequest
from app.agents.runtime import AgentRuntime
from app.agents.runtime import InMemoryAgentStore
from app.agents.schemas import AgentRunStatus
from app.agents.tool_guard import DEFAULT_TOOL_DEFINITIONS
from app.agents.tool_guard import ToolGuard
from app.architectures.repository import InMemoryArchitectureRepository
from app.architectures.service import ArchitectureService
from app.core.errors import NotFoundAppError
from app.core.errors import PhaseConflictAppError
from app.documents.models import DocumentType
from app.documents.repository import InMemoryDocumentRepository
from app.documents.service import DocumentService
from app.projects.models import ProjectPhase
from app.projects.repository import InMemoryProjectRepository
from app.projects.service import ProjectService
from app.workflows.planning import PlanningWorkflowService


def valid_spec() -> dict:
    return {
        "project_id": "gcp-project",
        "region": "asia-northeast1",
        "nodes": [
            {
                "id": "backend",
                "type": "cloud_run",
                "name": "Backend",
                "parameters": {"memory": "512Mi"},
                "rationale": "APIを公開する",
                "cost_band": "low",
            }
        ],
        "edges": [],
    }


class StaticPlanningGenerator:
    def __init__(self, output: Any) -> None:
        self.output = output
        self.requests: list[GcpPlannerRequest] = []

    async def generate(self, request: GcpPlannerRequest) -> Any:
        self.requests.append(request)
        if isinstance(self.output, dict):
            return dict(self.output)
        return self.output


async def make_workflow(
    output: Any,
) -> tuple[ProjectService, InMemoryProjectRepository, DocumentService, ArchitectureService, PlanningWorkflowService]:
    project_repository = InMemoryProjectRepository()
    project_service = ProjectService(repository=project_repository)
    document_service = DocumentService(InMemoryDocumentRepository())
    architecture_service = ArchitectureService(InMemoryArchitectureRepository())
    workflow = PlanningWorkflowService(
        project_service=project_service,
        document_service=document_service,
        architecture_service=architecture_service,
        agent_runtime=AgentRuntime(
            store=InMemoryAgentStore(),
            tool_guard=ToolGuard(DEFAULT_TOOL_DEFINITIONS),
        ),
        generator=StaticPlanningGenerator(output),
    )
    return project_service, project_repository, document_service, architecture_service, workflow


class PlanningWorkflowServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_propose_architecture_transitions_and_saves_proposal(self) -> None:
        project_service, project_repository, document_service, architecture_service, workflow = await make_workflow(
            {
                "architecture_spec": valid_spec(),
                "rationale_md": "Cloud Run を採用する。",
                "cloudbuild_yaml": "steps: []",
                "gcloud_commands": ["gcloud run services list"],
            }
        )
        project = await project_service.create_project(
            owner_uid="user-1",
            name="Support Desk",
            idea="問い合わせ管理アプリ",
        )
        project.update_phase(ProjectPhase.DESIGN_APPROVED)
        await project_repository.update(project)
        await document_service.create_next_version(
            project_id=project.id,
            doc_type=DocumentType.REQUIREMENTS,
            content_md="# 要件定義書",
            generated_by="requirement_agent",
            prompt_text="requirements prompt",
        )
        await document_service.create_next_version(
            project_id=project.id,
            doc_type=DocumentType.BASIC_DESIGN,
            content_md="# 基本設計書",
            generated_by="architect_agent",
            prompt_text="basic prompt",
        )

        result = await workflow.propose_architecture(
            project_id=project.id,
            target_project_id="gcp-project",
        )
        updated_project = await project_repository.get(project.id)
        latest_proposal = await architecture_service.latest_payload(project.id)

        self.assertEqual(result.run.status, AgentRunStatus.SUCCEEDED)
        self.assertEqual(result.proposal.version, 1)
        self.assertEqual(latest_proposal["version"], 1)
        self.assertEqual(updated_project.phase, ProjectPhase.ARCHITECTURE_DRAFT)

    async def test_propose_architecture_rejects_wrong_phase_before_agent_run(self) -> None:
        project_service, project_repository, document_service, _, workflow = await make_workflow(
            {
                "architecture_spec": valid_spec(),
                "rationale_md": "Cloud Run を採用する。",
                "cloudbuild_yaml": "steps: []",
                "gcloud_commands": ["gcloud run services list"],
            }
        )
        project = await project_service.create_project(
            owner_uid="user-1",
            name="Support Desk",
            idea="問い合わせ管理アプリ",
        )
        project.update_phase(ProjectPhase.DEPLOYED)
        await project_repository.update(project)
        await document_service.create_next_version(
            project_id=project.id,
            doc_type=DocumentType.REQUIREMENTS,
            content_md="# 要件定義書",
            generated_by="requirement_agent",
            prompt_text="requirements prompt",
        )
        await document_service.create_next_version(
            project_id=project.id,
            doc_type=DocumentType.BASIC_DESIGN,
            content_md="# 基本設計書",
            generated_by="architect_agent",
            prompt_text="basic prompt",
        )

        with self.assertRaises(PhaseConflictAppError):
            await workflow.propose_architecture(
                project_id=project.id,
                target_project_id="gcp-project",
            )

    async def test_missing_basic_design_document_does_not_advance_phase(self) -> None:
        project_service, project_repository, document_service, _, workflow = await make_workflow(
            {
                "architecture_spec": valid_spec(),
                "rationale_md": "Use Cloud Run",
                "cloudbuild_yaml": "steps: []",
                "gcloud_commands": ["gcloud run services list"],
            }
        )
        project = await project_service.create_project(
            owner_uid="user-1",
            name="Support Desk",
            idea="Support desk app",
        )
        project.update_phase(ProjectPhase.DESIGN_APPROVED)
        await project_repository.update(project)
        await document_service.create_next_version(
            project_id=project.id,
            doc_type=DocumentType.REQUIREMENTS,
            content_md="# Requirements",
            generated_by="requirement_agent",
            prompt_text="requirements prompt",
        )

        with self.assertRaises(NotFoundAppError):
            await workflow.propose_architecture(
                project_id=project.id,
                target_project_id="gcp-project",
            )

        updated_project = await project_repository.get(project.id)
        self.assertEqual(updated_project.phase, ProjectPhase.DESIGN_APPROVED)


if __name__ == "__main__":
    unittest.main()
