import unittest
from typing import Any

from app.agents.roles import SECURITY_AGENT
from app.agents.runtime import AgentRuntime
from app.agents.runtime import InMemoryAgentStore
from app.agents.schemas import AgentRunStatus
from app.agents.security import SecurityAgent
from app.agents.security import SecurityEvaluationRequest
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
                "parameters": {},
                "rationale": "APIを公開する",
                "cost_band": "low",
            }
        ],
        "edges": [],
    }


class StaticSecurityEvaluator:
    def __init__(self, output: Any) -> None:
        self.output = output
        self.requests: list[SecurityEvaluationRequest] = []

    async def evaluate(self, request: SecurityEvaluationRequest) -> Any:
        self.requests.append(request)
        if isinstance(self.output, dict):
            return dict(self.output)
        return self.output


class SecurityAgentTests(unittest.IsolatedAsyncioTestCase):
    async def test_security_agent_validates_findings(self) -> None:
        runtime = AgentRuntime(
            store=InMemoryAgentStore(),
            tool_guard=ToolGuard(DEFAULT_TOOL_DEFINITIONS),
        )
        evaluator = StaticSecurityEvaluator(
            {
                "findings": [
                    {
                        "severity": "critical",
                        "category": "iam",
                        "message": "権限が広すぎる",
                        "suggestion": "最小権限にする",
                    }
                ]
            }
        )

        run = await runtime.run_agent(
            project_id="project-1",
            project_phase="SECURITY_REVIEW",
            role=SECURITY_AGENT,
            agent_path="/root/security_agent",
            agent=SecurityAgent(evaluator),
            input_snapshot={
                "target_type": "architecture",
                "target_id": "arch-1",
                "architecture_spec": valid_spec(),
            },
        )

        self.assertEqual(run.status, AgentRunStatus.SUCCEEDED)
        self.assertEqual(run.output["findings"][0]["severity"], "critical")
        self.assertEqual(evaluator.requests[0].target_id, "arch-1")

    async def test_security_agent_rejects_invalid_severity(self) -> None:
        runtime = AgentRuntime(
            store=InMemoryAgentStore(),
            tool_guard=ToolGuard(DEFAULT_TOOL_DEFINITIONS),
        )

        run = await runtime.run_agent(
            project_id="project-1",
            project_phase="SECURITY_REVIEW",
            role=SECURITY_AGENT,
            agent_path="/root/security_agent",
            agent=SecurityAgent(
                StaticSecurityEvaluator(
                    {
                        "findings": [
                            {
                                "severity": "high",
                                "category": "iam",
                                "message": "権限が広すぎる",
                                "suggestion": "最小権限にする",
                            }
                        ]
                    }
                )
            ),
            input_snapshot={
                "target_type": "architecture",
                "target_id": "arch-1",
                "architecture_spec": valid_spec(),
            },
        )

        self.assertEqual(run.status, AgentRunStatus.FAILED)
        self.assertEqual(run.error_code, "ValidationAppError")


if __name__ == "__main__":
    unittest.main()
