import unittest

from app.architectures.repository import InMemoryArchitectureRepository
from app.architectures.service import ArchitectureService
from app.core.errors import PhaseConflictAppError
from app.deployments.cloudbuild import LocalCloudBuildAdapter
from app.deployments.repository import InMemoryDeploymentRepository
from app.deployments.service import DeploymentService
from app.projects.models import ProjectPhase
from app.projects.repository import InMemoryProjectRepository
from app.projects.service import ProjectService
from app.workflows.apply import ApplyWorkflowService


def valid_spec() -> dict:
    return {
        "project_id": "demo-gcp-project",
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


class ApplyWorkflowServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_apply_latest_architecture_records_deployment_and_marks_deployed(self) -> None:
        project_repository = InMemoryProjectRepository()
        project_service = ProjectService(repository=project_repository)
        architecture_service = ArchitectureService(InMemoryArchitectureRepository())
        deployment_service = DeploymentService(InMemoryDeploymentRepository())
        workflow = ApplyWorkflowService(
            project_service=project_service,
            architecture_service=architecture_service,
            deployment_service=deployment_service,
            cloudbuild_adapter=LocalCloudBuildAdapter(),
        )
        project = await project_service.create_project(
            owner_uid="demo-user",
            name="Support Desk",
            idea="問い合わせ管理アプリ",
        )
        project.update_phase(ProjectPhase.ARCHITECTURE_APPROVED)
        await project_repository.update(project)
        await architecture_service.create_next_proposal(
            project_id=project.id,
            spec_payload=valid_spec(),
            rationale_md="Cloud Run を採用する。",
            cloudbuild_yaml="steps: []",
            gcloud_commands=("gcloud run services list",),
        )

        result = await workflow.apply_latest_architecture(project_id=project.id)
        latest_deployment = await deployment_service.latest_payload(project.id)
        updated_project = await project_service.get_project_payload(project.id)

        self.assertEqual(result.deployment.status.value, "succeeded")
        self.assertEqual(latest_deployment["status"], "succeeded")
        self.assertEqual(updated_project["phase"], "DEPLOYED")

    async def test_apply_rejects_unapproved_architecture_phase(self) -> None:
        project_service = ProjectService(repository=InMemoryProjectRepository())
        workflow = ApplyWorkflowService(
            project_service=project_service,
            architecture_service=ArchitectureService(InMemoryArchitectureRepository()),
            deployment_service=DeploymentService(InMemoryDeploymentRepository()),
            cloudbuild_adapter=LocalCloudBuildAdapter(),
        )
        project = await project_service.create_project(
            owner_uid="demo-user",
            name="Support Desk",
            idea="問い合わせ管理アプリ",
        )

        with self.assertRaises(PhaseConflictAppError):
            await workflow.apply_latest_architecture(project_id=project.id)


if __name__ == "__main__":
    unittest.main()
