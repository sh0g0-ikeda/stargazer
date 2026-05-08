import unittest
from typing import Any

from app.agents.requirement import RequirementAgent
from app.agents.requirement import RequirementGenerationRequest
from app.agents.roles import REQUIREMENT_AGENT
from app.agents.runtime import AgentRuntime
from app.agents.runtime import InMemoryAgentStore
from app.agents.schemas import AgentRunStatus
from app.agents.tool_guard import DEFAULT_TOOL_DEFINITIONS
from app.agents.tool_guard import ToolGuard


class StaticRequirementGenerator:
    def __init__(self, output: Any) -> None:
        self.output = output
        self.requests: list[RequirementGenerationRequest] = []

    async def generate(self, request: RequirementGenerationRequest) -> Any:
        self.requests.append(request)
        if isinstance(self.output, dict):
            return dict(self.output)
        return self.output


class RequirementAgentTests(unittest.IsolatedAsyncioTestCase):
    async def test_requirement_agent_validates_input_and_output(self) -> None:
        generator = StaticRequirementGenerator(
            {
                "requirements_doc_md": "# 要件定義書\n\n問い合わせを管理する。",
                "unresolved_items": ["認証方式"],
            }
        )
        store = InMemoryAgentStore()
        runtime = AgentRuntime(
            store=store,
            tool_guard=ToolGuard(DEFAULT_TOOL_DEFINITIONS),
        )

        run = await runtime.run_agent(
            project_id="project-1",
            project_phase="REQUIREMENT_DRAFT",
            role=REQUIREMENT_AGENT,
            agent_path="/root/requirement_agent",
            agent=RequirementAgent(generator),
            input_snapshot={
                "idea": "問い合わせ管理アプリ",
                "form_responses": {"users": "support team"},
                "follow_up_answers": {"auth": "Google Sign-in"},
            },
        )

        self.assertEqual(run.status, AgentRunStatus.SUCCEEDED)
        self.assertEqual(run.output["unresolved_items"], ["認証方式"])
        self.assertEqual(generator.requests[0].idea, "問い合わせ管理アプリ")

    async def test_requirement_agent_rejects_invalid_llm_output(self) -> None:
        generator = StaticRequirementGenerator(
            {
                "requirements_doc_md": "",
                "unresolved_items": [],
            }
        )
        store = InMemoryAgentStore()
        runtime = AgentRuntime(
            store=store,
            tool_guard=ToolGuard(DEFAULT_TOOL_DEFINITIONS),
        )

        run = await runtime.run_agent(
            project_id="project-1",
            project_phase="REQUIREMENT_DRAFT",
            role=REQUIREMENT_AGENT,
            agent_path="/root/requirement_agent",
            agent=RequirementAgent(generator),
            input_snapshot={
                "idea": "問い合わせ管理アプリ",
                "form_responses": {},
            },
        )

        self.assertEqual(run.status, AgentRunStatus.FAILED)
        self.assertEqual(run.error_code, "ValidationAppError")

    async def test_requirement_agent_rejects_non_object_llm_output(self) -> None:
        generator = StaticRequirementGenerator(["not", "an", "object"])
        store = InMemoryAgentStore()
        runtime = AgentRuntime(
            store=store,
            tool_guard=ToolGuard(DEFAULT_TOOL_DEFINITIONS),
        )

        run = await runtime.run_agent(
            project_id="project-1",
            project_phase="REQUIREMENT_DRAFT",
            role=REQUIREMENT_AGENT,
            agent_path="/root/requirement_agent",
            agent=RequirementAgent(generator),
            input_snapshot={
                "idea": "問い合わせ管理アプリ",
                "form_responses": {},
            },
        )

        self.assertEqual(run.status, AgentRunStatus.FAILED)
        self.assertEqual(run.error_code, "ValidationAppError")

    async def test_requirement_agent_rejects_malformed_follow_up_answers(self) -> None:
        generator = StaticRequirementGenerator(
            {
                "requirements_doc_md": "# 要件定義書",
                "unresolved_items": [],
            }
        )
        store = InMemoryAgentStore()
        runtime = AgentRuntime(
            store=store,
            tool_guard=ToolGuard(DEFAULT_TOOL_DEFINITIONS),
        )

        run = await runtime.run_agent(
            project_id="project-1",
            project_phase="REQUIREMENT_DRAFT",
            role=REQUIREMENT_AGENT,
            agent_path="/root/requirement_agent",
            agent=RequirementAgent(generator),
            input_snapshot={
                "idea": "問い合わせ管理アプリ",
                "form_responses": {},
                "follow_up_answers": {"auth": 123},
            },
        )

        self.assertEqual(run.status, AgentRunStatus.FAILED)
        self.assertEqual(run.error_code, "ValidationAppError")


if __name__ == "__main__":
    unittest.main()
