import unittest

from app.agents.runtime import AgentRuntime
from app.agents.runtime import InMemoryAgentStore
from app.agents.tool_guard import DEFAULT_TOOL_DEFINITIONS
from app.agents.tool_guard import ToolGuard
from app.api.facade import StarGazerApiFacade
from app.architectures.repository import InMemoryArchitectureRepository
from app.architectures.service import ArchitectureService
from app.documents.repository import InMemoryDocumentRepository
from app.documents.service import DocumentService
from app.projects.repository import InMemoryProjectRepository
from app.projects.service import ProjectService
from app.security.repository import InMemorySecurityFindingRepository
from app.security.service import SecurityFindingService
from app.workflows.demo import DemoArchitectGenerator
from app.workflows.demo import DemoGcpPlannerGenerator
from app.workflows.demo import DemoRequirementGenerator
from app.workflows.demo import DemoSecurityEvaluator
from app.workflows.designs import DesignWorkflowService
from app.workflows.planning import PlanningWorkflowService
from app.workflows.requirements import RequirementWorkflowService
from app.workflows.security import SecurityEvaluationWorkflowService


def make_facade() -> StarGazerApiFacade:
    project_service = ProjectService(repository=InMemoryProjectRepository())
    document_service = DocumentService(InMemoryDocumentRepository())
    architecture_service = ArchitectureService(InMemoryArchitectureRepository())
    agent_runtime = AgentRuntime(
        store=InMemoryAgentStore(),
        tool_guard=ToolGuard(DEFAULT_TOOL_DEFINITIONS),
    )
    return StarGazerApiFacade(
        project_service=project_service,
        requirement_workflow=RequirementWorkflowService(
            project_service=project_service,
            document_service=document_service,
            agent_runtime=agent_runtime,
            generator=DemoRequirementGenerator(),
        ),
        design_workflow=DesignWorkflowService(
            project_service=project_service,
            document_service=document_service,
            agent_runtime=agent_runtime,
            generator=DemoArchitectGenerator(),
        ),
        planning_workflow=PlanningWorkflowService(
            project_service=project_service,
            document_service=document_service,
            architecture_service=architecture_service,
            agent_runtime=agent_runtime,
            generator=DemoGcpPlannerGenerator(),
        ),
        security_workflow=SecurityEvaluationWorkflowService(
            project_service=project_service,
            architecture_service=architecture_service,
            finding_service=SecurityFindingService(InMemorySecurityFindingRepository()),
            agent_runtime=agent_runtime,
            evaluator=DemoSecurityEvaluator(),
        ),
    )


class StarGazerApiFacadeTests(unittest.IsolatedAsyncioTestCase):
    async def test_create_project_returns_api_response(self) -> None:
        facade = make_facade()

        response = await facade.create_project(
            owner_uid="user-1",
            name="Support Desk",
            idea="問い合わせ管理アプリ",
            request_id="request-1",
        )
        body = response.to_dict()

        self.assertIsNone(body["error"])
        self.assertEqual(body["data"]["phase"], "DRAFT")
        self.assertEqual(body["meta"]["request_id"], "request-1")

    async def test_create_project_validation_error_uses_error_envelope(self) -> None:
        facade = make_facade()

        response = await facade.create_project(
            owner_uid="user-1",
            name=" ",
            idea="問い合わせ管理アプリ",
            request_id="request-1",
        )
        body = response.to_dict()

        self.assertIsNone(body["data"])
        self.assertEqual(body["error"]["code"], "VALIDATION_ERROR")
        self.assertEqual(body["meta"]["request_id"], "request-1")


if __name__ == "__main__":
    unittest.main()
