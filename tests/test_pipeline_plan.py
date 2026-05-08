import unittest

from app.core.errors import ValidationAppError
from app.deployments.pipeline import render_cloud_run_apply_plan


def architecture_payload() -> dict:
    return {
        "id": "arch-1",
        "spec": {
            "project_id": "demo-gcp-project",
            "region": "asia-northeast1",
            "nodes": [
                {
                    "id": "backend_api",
                    "type": "cloud_run",
                    "name": "Backend API",
                    "parameters": {
                        "memory": "512Mi",
                        "cpu": "1",
                        "min_instances": 0,
                        "max_instances": 5,
                    },
                    "rationale": "Runs the API.",
                    "cost_band": "low",
                }
            ],
            "edges": [],
        },
    }


class CloudBuildApplyPlanTests(unittest.TestCase):
    def test_render_cloud_run_apply_plan_contains_deploy_command(self) -> None:
        plan = render_cloud_run_apply_plan(architecture_payload=architecture_payload())

        self.assertEqual(plan.project_id, "demo-gcp-project")
        self.assertEqual(plan.region, "asia-northeast1")
        self.assertEqual(plan.service_name, "backend-api")
        self.assertIn("gcloud run deploy backend-api", plan.gcloud_commands[-1])
        self.assertIn("--no-allow-unauthenticated", plan.gcloud_commands[-1])
        self.assertIn("gcr.io/cloud-builders/docker", plan.cloudbuild_yaml)

    def test_render_cloud_run_apply_plan_rejects_invalid_project_id(self) -> None:
        payload = architecture_payload()
        payload["spec"]["project_id"] = "INVALID_PROJECT"

        with self.assertRaises(ValidationAppError):
            render_cloud_run_apply_plan(architecture_payload=payload)

    def test_render_cloud_run_apply_plan_rejects_missing_cloud_run_node(self) -> None:
        payload = architecture_payload()
        payload["spec"]["nodes"] = []

        with self.assertRaises(ValidationAppError):
            render_cloud_run_apply_plan(architecture_payload=payload)


if __name__ == "__main__":
    unittest.main()
