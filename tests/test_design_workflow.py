import unittest
from typing import Any

from app.agents.architect import ArchitectGenerationRequest
from app.agents.runtime import AgentRuntime
from app.agents.runtime import InMemoryAgentStore
from app.agents.schemas import AgentRunStatus
from app.agents.tool_guard import DEFAULT_TOOL_DEFINITIONS
from app.agents.tool_guard import ToolGuard
from app.core.errors import PhaseConflictAppError
from app.core.errors import ValidationAppError
from app.documents.models import DocumentType
from app.documents.repository import InMemoryDocumentRepository
from app.documents.service import DocumentService
from app.projects.models import ProjectPhase
from app.projects.repository import InMemoryProjectRepository
from app.projects.service import ProjectService
from app.workflows.designs import DesignWorkflowService


class StaticDesignGenerator:
    def __init__(self, output: Any) -> None:
        self.output = output
        self.requests: list[ArchitectGenerationRequest] = []

    async def generate(self, request: ArchitectGenerationRequest) -> Any:
        self.requests.append(request)
        if isinstance(self.output, dict):
            return dict(self.output)
        return self.output


async def make_design_workflow(
    output: Any,
) -> tuple[ProjectService, InMemoryProjectRepository, DocumentService, InMemoryDocumentRepository, DesignWorkflowService]:
    project_repository = InMemoryProjectRepository()
    project_service = ProjectService(repository=project_repository)
    document_repository = InMemoryDocumentRepository()
    document_service = DocumentService(document_repository)
    workflow = DesignWorkflowService(
        project_service=project_service,
        document_service=document_service,
        agent_runtime=AgentRuntime(
            store=InMemoryAgentStore(),
            tool_guard=ToolGuard(DEFAULT_TOOL_DEFINITIONS),
        ),
        generator=StaticDesignGenerator(output),
    )
    return project_service, project_repository, document_service, document_repository, workflow


class DesignWorkflowServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_generate_design_document_transitions_and_saves_document(self) -> None:
        project_service, project_repository, document_service, document_repository, workflow = await make_design_workflow(
            {
                "doc_md": "# 基本設計書\n\n設計内容。",
                "references": ["adr:001"],
            }
        )
        project = await project_service.create_project(
            owner_uid="user-1",
            name="Support Desk",
            idea="問い合わせ管理アプリ",
        )
        project.update_phase(ProjectPhase.REQUIREMENT_APPROVED)
        await project_repository.update(project)
        await document_service.create_next_version(
            project_id=project.id,
            doc_type=DocumentType.REQUIREMENTS,
            content_md="# 要件定義書",
            generated_by="requirement_agent",
            prompt_text="requirements prompt",
        )

        result = await workflow.generate_design_document(
            project_id=project.id,
            doc_type=DocumentType.BASIC_DESIGN,
        )

        updated_project = await project_repository.get(project.id)
        versions = await document_repository.list_versions(project.id, DocumentType.BASIC_DESIGN)

        self.assertEqual(result.run.status, AgentRunStatus.SUCCEEDED)
        self.assertEqual(result.document.version, 1)
        self.assertEqual(len(versions), 1)
        self.assertEqual(updated_project.phase, ProjectPhase.DESIGN_DRAFT)
        self.assertIn("adr:001", result.document.references)

    async def test_generate_design_document_rejects_invalid_doc_type(self) -> None:
        project_service, _, _, _, workflow = await make_design_workflow({"doc_md": "# Doc"})
        project = await project_service.create_project(
            owner_uid="user-1",
            name="Support Desk",
            idea="問い合わせ管理アプリ",
        )

        with self.assertRaises(ValidationAppError):
            await workflow.generate_design_document(
                project_id=project.id,
                doc_type=DocumentType.REQUIREMENTS,
            )

    async def test_generate_design_document_rejects_wrong_phase_before_agent_run(self) -> None:
        project_service, project_repository, document_service, _, workflow = await make_design_workflow(
            {"doc_md": "# 基本設計書"}
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

        with self.assertRaises(PhaseConflictAppError):
            await workflow.generate_design_document(
                project_id=project.id,
                doc_type=DocumentType.BASIC_DESIGN,
            )


if __name__ == "__main__":
    unittest.main()
