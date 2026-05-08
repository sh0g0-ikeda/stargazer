import unittest
from typing import Any

from app.agents.architect import ArchitectAgent
from app.agents.architect import ArchitectGenerationRequest
from app.agents.roles import ARCHITECT_AGENT
from app.agents.runtime import AgentRuntime
from app.agents.runtime import InMemoryAgentStore
from app.agents.schemas import AgentRunStatus
from app.agents.tool_guard import DEFAULT_TOOL_DEFINITIONS
from app.agents.tool_guard import ToolGuard


class StaticArchitectGenerator:
    def __init__(self, output: Any) -> None:
        self.output = output
        self.requests: list[ArchitectGenerationRequest] = []

    async def generate(self, request: ArchitectGenerationRequest) -> Any:
        self.requests.append(request)
        if isinstance(self.output, dict):
            return dict(self.output)
        return self.output


class ArchitectAgentTests(unittest.IsolatedAsyncioTestCase):
    async def test_architect_agent_validates_input_and_output(self) -> None:
        generator = StaticArchitectGenerator(
            {
                "doc_md": "# 基本設計書\n\n構成を定義する。",
                "references": [" requirements:v1 "],
            }
        )
        runtime = AgentRuntime(
            store=InMemoryAgentStore(),
            tool_guard=ToolGuard(DEFAULT_TOOL_DEFINITIONS),
        )

        run = await runtime.run_agent(
            project_id="project-1",
            project_phase="DESIGN_DRAFT",
            role=ARCHITECT_AGENT,
            agent_path="/root/architect_agent",
            agent=ArchitectAgent(generator),
            input_snapshot={
                "requirements_doc_md": "# 要件定義書",
                "doc_type": "basic_design",
            },
        )

        self.assertEqual(run.status, AgentRunStatus.SUCCEEDED)
        self.assertEqual(run.output["references"], ["requirements:v1"])
        self.assertEqual(generator.requests[0].doc_type.value, "basic_design")

    async def test_architect_agent_rejects_requirement_doc_type(self) -> None:
        runtime = AgentRuntime(
            store=InMemoryAgentStore(),
            tool_guard=ToolGuard(DEFAULT_TOOL_DEFINITIONS),
        )

        run = await runtime.run_agent(
            project_id="project-1",
            project_phase="DESIGN_DRAFT",
            role=ARCHITECT_AGENT,
            agent_path="/root/architect_agent",
            agent=ArchitectAgent(StaticArchitectGenerator({"doc_md": "# Doc"})),
            input_snapshot={
                "requirements_doc_md": "# 要件定義書",
                "doc_type": "requirements",
            },
        )

        self.assertEqual(run.status, AgentRunStatus.FAILED)
        self.assertEqual(run.error_code, "ValidationAppError")

    async def test_architect_agent_rejects_non_object_output(self) -> None:
        runtime = AgentRuntime(
            store=InMemoryAgentStore(),
            tool_guard=ToolGuard(DEFAULT_TOOL_DEFINITIONS),
        )

        run = await runtime.run_agent(
            project_id="project-1",
            project_phase="DESIGN_DRAFT",
            role=ARCHITECT_AGENT,
            agent_path="/root/architect_agent",
            agent=ArchitectAgent(StaticArchitectGenerator(["not", "an", "object"])),
            input_snapshot={
                "requirements_doc_md": "# 要件定義書",
                "doc_type": "api_design",
            },
        )

        self.assertEqual(run.status, AgentRunStatus.FAILED)
        self.assertEqual(run.error_code, "ValidationAppError")


if __name__ == "__main__":
    unittest.main()
