import unittest

from app.bootstrap import build_demo_facade


class BootstrapTests(unittest.IsolatedAsyncioTestCase):
    async def test_build_demo_facade_wires_core_workflow(self) -> None:
        facade = build_demo_facade()

        create_response = await facade.create_project(
            name="Support Desk",
            idea="問い合わせ管理アプリ",
        )
        project_id = create_response.to_dict()["data"]["id"]
        follow_up_response = await facade.generate_follow_up_questions(project_id=project_id)

        self.assertIsNone(follow_up_response.to_dict()["error"])
        self.assertEqual(
            follow_up_response.to_dict()["data"]["run_status"],
            "SUCCEEDED",
        )


if __name__ == "__main__":
    unittest.main()
