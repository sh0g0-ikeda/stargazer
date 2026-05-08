import unittest

from app.workflows.demo import build_requirement_demo_response


class DemoWorkflowTests(unittest.IsolatedAsyncioTestCase):
    async def test_requirement_demo_response_uses_api_envelope(self) -> None:
        response = await build_requirement_demo_response(
            idea="問い合わせ管理アプリ",
            owner_uid="local-user",
        )
        body = response.to_dict()

        self.assertIsNone(body["error"])
        self.assertEqual(body["data"]["run_status"], "SUCCEEDED")
        self.assertEqual(body["data"]["document_version"], 1)
        self.assertEqual(body["data"]["unresolved_items"], ["認証方式"])


if __name__ == "__main__":
    unittest.main()
