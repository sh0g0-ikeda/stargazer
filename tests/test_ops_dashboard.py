import unittest

from app.architectures.repository import InMemoryArchitectureRepository
from app.architectures.service import ArchitectureService
from app.deployments.repository import InMemoryDeploymentRepository
from app.deployments.service import DeploymentService
from app.ops.service import OpsDashboardService
from app.projects.repository import InMemoryProjectRepository
from app.projects.service import ProjectService
from app.security.repository import InMemorySecurityFindingRepository
from app.security.service import SecurityFindingService
from app.timeline.repository import InMemoryTimelineRepository
from app.timeline.service import TimelineService


class OpsDashboardServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_overview_returns_all_eight_sections(self) -> None:
        project_service = ProjectService(repository=InMemoryProjectRepository())
        service = OpsDashboardService(
            project_service=project_service,
            architecture_service=ArchitectureService(InMemoryArchitectureRepository()),
            deployment_service=DeploymentService(InMemoryDeploymentRepository()),
            finding_service=SecurityFindingService(InMemorySecurityFindingRepository()),
            timeline_service=TimelineService(InMemoryTimelineRepository()),
        )
        project = await project_service.create_project(
            owner_uid="demo-user",
            name="Support Desk",
            idea="問い合わせ管理アプリ",
        )

        payload = await service.overview(project_id=project.id)

        self.assertEqual(
            set(payload),
            {
                "system_overview",
                "architecture_map",
                "deployment_status",
                "logs_errors",
                "cost_overview",
                "security_overview",
                "agent_actions",
                "recommended_next_actions",
            },
        )
        self.assertEqual(payload["system_overview"]["phase"], "DRAFT")


if __name__ == "__main__":
    unittest.main()
