import unittest
from typing import Any

from app.agents.gcp_planner import GcpPlannerAgent
from app.agents.gcp_planner import GcpPlannerRequest
from app.agents.roles import GCP_PLANNER_AGENT
from app.agents.runtime import AgentRuntime
from app.agents.runtime import InMemoryAgentStore
from app.agents.schemas import AgentRunStatus
from app.agents.tool_guard import DEFAULT_TOOL_DEFINITIONS
from app.agents.tool_guard import ToolGuard


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


class StaticPlannerGenerator:
    def __init__(self, output: Any) -> None:
        self.output = output
        self.requests: list[GcpPlannerRequest] = []

    async def generate(self, request: GcpPlannerRequest) -> Any:
        self.requests.append(request)
        if isinstance(self.output, dict):
            return dict(self.output)
        return self.output


class GcpPlannerAgentTests(unittest.IsolatedAsyncioTestCase):
    async def test_planner_agent_validates_input_and_output(self) -> None:
        generator = StaticPlannerGenerator(
            {
                "architecture_spec": valid_spec(),
                "rationale_md": "Cloud Run を採用する。",
                "cloudbuild_yaml": "steps: []",
                "gcloud_commands": [" gcloud run services list "],
            }
        )
        runtime = AgentRuntime(
            store=InMemoryAgentStore(),
            tool_guard=ToolGuard(DEFAULT_TOOL_DEFINITIONS),
        )

        run = await runtime.run_agent(
            project_id="project-1",
            project_phase="ARCHITECTURE_DRAFT",
            role=GCP_PLANNER_AGENT,
            agent_path="/root/gcp_planner_agent",
            agent=GcpPlannerAgent(generator),
            input_snapshot={
                "requirements_doc_md": "# 要件定義書",
                "basic_design_md": "# 基本設計書",
                "target_project_id": "gcp-project",
            },
        )

        self.assertEqual(run.status, AgentRunStatus.SUCCEEDED)
        self.assertEqual(run.output["gcloud_commands"], ["gcloud run services list"])
        self.assertEqual(generator.requests[0].target_project_id, "gcp-project")

    async def test_planner_agent_rejects_invalid_architecture_edges(self) -> None:
        spec = valid_spec()
        spec["edges"][0]["to_node"] = "missing"
        runtime = AgentRuntime(
            store=InMemoryAgentStore(),
            tool_guard=ToolGuard(DEFAULT_TOOL_DEFINITIONS),
        )

        run = await runtime.run_agent(
            project_id="project-1",
            project_phase="ARCHITECTURE_DRAFT",
            role=GCP_PLANNER_AGENT,
            agent_path="/root/gcp_planner_agent",
            agent=GcpPlannerAgent(
                StaticPlannerGenerator(
                    {
                        "architecture_spec": spec,
                        "rationale_md": "Cloud Run を採用する。",
                        "cloudbuild_yaml": "steps: []",
                        "gcloud_commands": ["gcloud run services list"],
                    }
                )
            ),
            input_snapshot={
                "requirements_doc_md": "# 要件定義書",
                "basic_design_md": "# 基本設計書",
                "target_project_id": "gcp-project",
            },
        )

        self.assertEqual(run.status, AgentRunStatus.FAILED)
        self.assertEqual(run.error_code, "ValidationAppError")


if __name__ == "__main__":
    unittest.main()
