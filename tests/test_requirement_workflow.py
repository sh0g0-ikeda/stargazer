import unittest
from typing import Any

from app.agents.requirement import RequirementGenerationRequest
from app.agents.runtime import AgentRuntime
from app.agents.runtime import InMemoryAgentStore
from app.agents.schemas import AgentRunStatus
from app.agents.tool_guard import DEFAULT_TOOL_DEFINITIONS
from app.agents.tool_guard import ToolGuard
from app.core.errors import PhaseConflictAppError
from app.documents.models import DocumentType
from app.documents.repository import InMemoryDocumentRepository
from app.documents.service import DocumentService
from app.projects.models import ProjectPhase
from app.projects.repository import InMemoryProjectRepository
from app.projects.service import ProjectService
from app.workflows.requirements import RequirementWorkflowService


class WorkflowRequirementGenerator:
    def __init__(self, output: dict[str, Any]) -> None:
        self.output = output
        self.requests: list[RequirementGenerationRequest] = []

    async def generate(self, request: RequirementGenerationRequest) -> dict[str, Any]:
        self.requests.append(request)
        return dict(self.output)


class RequirementWorkflowServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_generate_requirements_transitions_project_and_saves_document(self) -> None:
        project_repository = InMemoryProjectRepository()
        project_service = ProjectService(repository=project_repository)
        document_repository = InMemoryDocumentRepository()
        workflow = RequirementWorkflowService(
            project_service=project_service,
            document_service=DocumentService(document_repository),
            agent_runtime=AgentRuntime(
                store=InMemoryAgentStore(),
                tool_guard=ToolGuard(DEFAULT_TOOL_DEFINITIONS),
            ),
            generator=WorkflowRequirementGenerator(
                {
                    "requirements_doc_md": "# 要件定義書\n\n問い合わせ管理。",
                    "unresolved_items": [],
                }
            ),
        )
        project = await project_service.create_project(
            owner_uid="user-1",
            name="Support Desk",
            idea="問い合わせ管理アプリ",
        )

        result = await workflow.generate_requirements(
            project_id=project.id,
            form_responses={"users": "support"},
            follow_up_answers={"auth": "Google"},
        )

        updated_project = await project_repository.get(project.id)
        versions = await document_repository.list_versions(project.id, DocumentType.REQUIREMENTS)

        self.assertEqual(result.run.status, AgentRunStatus.SUCCEEDED)
        self.assertIsNotNone(result.document)
        self.assertEqual(result.document.version, 1)
        self.assertEqual(len(versions), 1)
        self.assertEqual(updated_project.phase, ProjectPhase.REQUIREMENT_DRAFT)

    async def test_failed_requirement_run_does_not_save_document(self) -> None:
        project_repository = InMemoryProjectRepository()
        project_service = ProjectService(repository=project_repository)
        document_repository = InMemoryDocumentRepository()
        workflow = RequirementWorkflowService(
            project_service=project_service,
            document_service=DocumentService(document_repository),
            agent_runtime=AgentRuntime(
                store=InMemoryAgentStore(),
                tool_guard=ToolGuard(DEFAULT_TOOL_DEFINITIONS),
            ),
            generator=WorkflowRequirementGenerator(
                {
                    "requirements_doc_md": "",
                    "unresolved_items": [],
                }
            ),
        )
        project = await project_service.create_project(
            owner_uid="user-1",
            name="Support Desk",
            idea="問い合わせ管理アプリ",
        )

        result = await workflow.generate_requirements(project_id=project.id)
        versions = await document_repository.list_versions(project.id, DocumentType.REQUIREMENTS)

        self.assertEqual(result.run.status, AgentRunStatus.FAILED)
        self.assertIsNone(result.document)
        self.assertEqual(versions, [])

    async def test_generate_follow_up_questions_transitions_project(self) -> None:
        project_repository = InMemoryProjectRepository()
        project_service = ProjectService(repository=project_repository)
        workflow = RequirementWorkflowService(
            project_service=project_service,
            document_service=DocumentService(InMemoryDocumentRepository()),
            agent_runtime=AgentRuntime(
                store=InMemoryAgentStore(),
                tool_guard=ToolGuard(DEFAULT_TOOL_DEFINITIONS),
            ),
            generator=WorkflowRequirementGenerator(
                {
                    "follow_up_questions": [
                        "認証方式は必要ですか。",
                        "保存したいデータは何ですか。",
                    ],
                    "requirements_doc_md": "# 要件定義書",
                    "unresolved_items": [],
                }
            ),
        )
        project = await project_service.create_project(
            owner_uid="user-1",
            name="Support Desk",
            idea="問い合わせ管理アプリ",
        )

        result = await workflow.generate_follow_up_questions(
            project_id=project.id,
            form_responses={"users": "support"},
        )
        updated_project = await project_repository.get(project.id)

        self.assertEqual(result.run.status, AgentRunStatus.SUCCEEDED)
        self.assertEqual(len(result.questions), 2)
        self.assertEqual(updated_project.phase, ProjectPhase.REQUIREMENT_DRAFT)

    async def test_generate_requirements_rejects_unrelated_phase_before_agent_run(self) -> None:
        project_repository = InMemoryProjectRepository()
        project_service = ProjectService(repository=project_repository)
        document_repository = InMemoryDocumentRepository()
        workflow = RequirementWorkflowService(
            project_service=project_service,
            document_service=DocumentService(document_repository),
            agent_runtime=AgentRuntime(
                store=InMemoryAgentStore(),
                tool_guard=ToolGuard(DEFAULT_TOOL_DEFINITIONS),
            ),
            generator=WorkflowRequirementGenerator(
                {
                    "requirements_doc_md": "# 要件定義書",
                    "unresolved_items": [],
                }
            ),
        )
        project = await project_service.create_project(
            owner_uid="user-1",
            name="Support Desk",
            idea="問い合わせ管理アプリ",
        )
        project.update_phase(ProjectPhase.DEPLOYED)
        await project_repository.update(project)

        with self.assertRaises(PhaseConflictAppError):
            await workflow.generate_requirements(project_id=project.id)


if __name__ == "__main__":
    unittest.main()
