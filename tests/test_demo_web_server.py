import json
import unittest

from app.bootstrap import build_demo_facade
from app.core.errors import ValidationAppError
from app.web.demo_server import DemoWebApp


class DemoWebServerTests(unittest.IsolatedAsyncioTestCase):
    async def test_health_endpoint_returns_ok(self) -> None:
        app = DemoWebApp(build_demo_facade(), target_project_id="demo-gcp-project")

        status, content_type, body = await app.handle(method="GET", raw_path="/api/health")
        payload = json.loads(body.decode("utf-8"))

        self.assertEqual(status, 200)
        self.assertEqual(content_type, "application/json; charset=utf-8")
        self.assertEqual(payload["data"], {"status": "ok"})

    async def test_project_pipeline_routes_reach_facade(self) -> None:
        app = DemoWebApp(build_demo_facade(), target_project_id="demo-gcp-project")

        _, _, create_body = await app.handle(
            method="POST",
            raw_path="/api/projects",
            body=json.dumps({"name": "Support Desk", "idea": "support desk app"}).encode("utf-8"),
        )
        project_id = json.loads(create_body.decode("utf-8"))["data"]["id"]

        status, _, requirements_body = await app.handle(
            method="POST",
            raw_path=f"/api/projects/{project_id}/requirements",
            body=b"{}",
        )
        payload = json.loads(requirements_body.decode("utf-8"))

        self.assertEqual(status, 200)
        self.assertEqual(payload["data"]["run_status"], "SUCCEEDED")

    async def test_invalid_json_returns_validation_error(self) -> None:
        app = DemoWebApp(build_demo_facade(), target_project_id="demo-gcp-project")

        with self.assertRaisesRegex(ValidationAppError, "request body must be valid JSON"):
            await app.handle(method="POST", raw_path="/api/projects", body=b"{")


if __name__ == "__main__":
    unittest.main()
