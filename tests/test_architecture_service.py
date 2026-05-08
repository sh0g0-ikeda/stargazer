import unittest

from app.architectures.repository import InMemoryArchitectureRepository
from app.architectures.service import ArchitectureService
from app.core.errors import ValidationAppError


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
                "security_notes": ["認証を必須にする"],
            },
            {
                "id": "db",
                "type": "firestore",
                "name": "Firestore",
                "parameters": {},
                "rationale": "状態を保存する",
                "cost_band": "low",
            },
        ],
        "edges": [
            {
                "id": "backend-db",
                "from_node": "backend",
                "to_node": "db",
                "type": "db_rw",
                "description": "読み書き",
            }
        ],
    }


class ArchitectureServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_create_next_proposal_validates_and_versions_spec(self) -> None:
        service = ArchitectureService(InMemoryArchitectureRepository())

        first = await service.create_next_proposal(
            project_id="project-1",
            spec_payload=valid_spec(),
            rationale_md="採用理由",
            cloudbuild_yaml="steps: []",
            gcloud_commands=("gcloud run services list",),
        )
        second = await service.create_next_proposal(
            project_id="project-1",
            spec_payload=valid_spec(),
            rationale_md="採用理由",
            cloudbuild_yaml="steps: []",
            gcloud_commands=("gcloud run services list",),
        )

        self.assertEqual(first.version, 1)
        self.assertEqual(second.version, 2)
        self.assertEqual(first.spec.nodes[0].id, "backend")

    async def test_latest_payload_is_json_safe(self) -> None:
        service = ArchitectureService(InMemoryArchitectureRepository())
        proposal = await service.create_next_proposal(
            project_id="project-1",
            spec_payload=valid_spec(),
            rationale_md="採用理由",
            cloudbuild_yaml="steps: []",
            gcloud_commands=("gcloud run services list",),
        )

        payload = await service.latest_payload("project-1")

        self.assertEqual(payload["id"], proposal.id)
        self.assertEqual(payload["status"], "proposed")
        self.assertEqual(payload["spec"]["nodes"][0]["type"], "cloud_run")
        self.assertEqual(payload["spec"]["edges"][0]["type"], "db_rw")

    async def test_create_next_proposal_rejects_edges_to_missing_nodes(self) -> None:
        service = ArchitectureService(InMemoryArchitectureRepository())
        spec = valid_spec()
        spec["edges"][0]["to_node"] = "missing"

        with self.assertRaises(ValidationAppError):
            await service.create_next_proposal(
                project_id="project-1",
                spec_payload=spec,
                rationale_md="採用理由",
                cloudbuild_yaml="steps: []",
                gcloud_commands=("gcloud run services list",),
            )

    async def test_create_next_proposal_rejects_empty_commands(self) -> None:
        service = ArchitectureService(InMemoryArchitectureRepository())

        with self.assertRaises(ValidationAppError):
            await service.create_next_proposal(
                project_id="project-1",
                spec_payload=valid_spec(),
                rationale_md="採用理由",
                cloudbuild_yaml="steps: []",
                gcloud_commands=(" ",),
            )

    async def test_editable_node_parameters_returns_allowed_fields(self) -> None:
        service = ArchitectureService(InMemoryArchitectureRepository())
        await service.create_next_proposal(
            project_id="project-1",
            spec_payload=valid_spec(),
            rationale_md="採用理由",
            cloudbuild_yaml="steps: []",
            gcloud_commands=("gcloud run services list",),
        )

        payload = await service.editable_node_parameters(
            project_id="project-1",
            node_id="backend",
        )

        self.assertIn("memory", payload["editable_fields"])
        self.assertEqual(payload["current_parameters"]["memory"], "512Mi")

    async def test_update_node_creates_new_proposal_version(self) -> None:
        service = ArchitectureService(InMemoryArchitectureRepository())
        await service.create_next_proposal(
            project_id="project-1",
            spec_payload=valid_spec(),
            rationale_md="採用理由",
            cloudbuild_yaml="steps: []",
            gcloud_commands=("gcloud run services list",),
        )

        proposal = await service.create_updated_node_proposal(
            project_id="project-1",
            node_id="backend",
            parameter_patch={"memory": "1Gi"},
            change_reason="デモ負荷に備える",
        )

        self.assertEqual(proposal.version, 2)
        self.assertEqual(proposal.spec.nodes[0].parameters["memory"], "1Gi")

    async def test_delete_node_requires_confirmation(self) -> None:
        service = ArchitectureService(InMemoryArchitectureRepository())
        await service.create_next_proposal(
            project_id="project-1",
            spec_payload=valid_spec(),
            rationale_md="採用理由",
            cloudbuild_yaml="steps: []",
            gcloud_commands=("gcloud run services list",),
        )

        with self.assertRaises(ValidationAppError):
            await service.create_deleted_node_proposal(
                project_id="project-1",
                node_id="backend",
                confirmed=False,
                change_reason="不要になった",
            )


if __name__ == "__main__":
    unittest.main()
