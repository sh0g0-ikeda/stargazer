import unittest

from app.agents.schemas import AgentRole
from app.agents.schemas import ToolRequest
from app.agents.tool_guard import DEFAULT_TOOL_DEFINITIONS
from app.agents.tool_guard import ToolGuard
from app.tools.runtime import ToolExecutionContext
from app.tools.runtime import ToolRuntime


class ToolRuntimeTests(unittest.IsolatedAsyncioTestCase):
    async def test_execute_calls_handler_after_policy_allows_request(self) -> None:
        calls: list[dict] = []

        async def handler(arguments: dict) -> dict:
            calls.append(arguments)
            return {"ok": True}

        runtime = ToolRuntime(
            tool_guard=ToolGuard(DEFAULT_TOOL_DEFINITIONS),
            handlers={"write_document": handler},
        )
        result = await runtime.execute(
            request=ToolRequest("write_document", {"doc_type": "requirements"}),
            context=ToolExecutionContext(
                role=AgentRole(
                    name="test_agent",
                    model="test-model",
                    thinking_level="low",
                    allowed_tools=frozenset({"write_document"}),
                ),
                project_phase="REQUIREMENT_DRAFT",
                approved_tool_names=frozenset(),
            ),
        )

        self.assertTrue(result.decision.allowed)
        self.assertEqual(result.output, {"ok": True})
        self.assertEqual(calls, [{"doc_type": "requirements"}])

    async def test_execute_does_not_call_destructive_handler_without_approval(self) -> None:
        calls: list[dict] = []

        async def handler(arguments: dict) -> dict:
            calls.append(arguments)
            return {"build_id": "build-1"}

        runtime = ToolRuntime(
            tool_guard=ToolGuard(DEFAULT_TOOL_DEFINITIONS),
            handlers={"trigger_cloud_build": handler},
        )
        result = await runtime.execute(
            request=ToolRequest("trigger_cloud_build", {}),
            context=ToolExecutionContext(
                role=AgentRole(
                    name="apply_agent",
                    model="test-model",
                    thinking_level="low",
                    allowed_tools=frozenset({"trigger_cloud_build"}),
                ),
                project_phase="READY_TO_APPLY",
                approved_tool_names=frozenset(),
            ),
        )

        self.assertFalse(result.decision.allowed)
        self.assertEqual(result.decision.code, "APPROVAL_REQUIRED")
        self.assertEqual(calls, [])

    async def test_execute_reports_missing_handler_after_policy_allows_request(self) -> None:
        runtime = ToolRuntime(
            tool_guard=ToolGuard(DEFAULT_TOOL_DEFINITIONS),
            handlers={},
        )
        result = await runtime.execute(
            request=ToolRequest("write_document", {"doc_type": "requirements"}),
            context=ToolExecutionContext(
                role=AgentRole(
                    name="test_agent",
                    model="test-model",
                    thinking_level="low",
                    allowed_tools=frozenset({"write_document"}),
                ),
                project_phase="REQUIREMENT_DRAFT",
                approved_tool_names=frozenset(),
            ),
        )

        self.assertFalse(result.decision.allowed)
        self.assertEqual(result.decision.code, "TOOL_HANDLER_NOT_FOUND")

    async def test_execute_rejects_non_object_handler_output(self) -> None:
        async def handler(arguments: dict) -> list[str]:
            return ["invalid"]

        runtime = ToolRuntime(
            tool_guard=ToolGuard(DEFAULT_TOOL_DEFINITIONS),
            handlers={"write_document": handler},
        )
        result = await runtime.execute(
            request=ToolRequest("write_document", {"doc_type": "requirements"}),
            context=ToolExecutionContext(
                role=AgentRole(
                    name="test_agent",
                    model="test-model",
                    thinking_level="low",
                    allowed_tools=frozenset({"write_document"}),
                ),
                project_phase="REQUIREMENT_DRAFT",
                approved_tool_names=frozenset(),
            ),
        )

        self.assertFalse(result.decision.allowed)
        self.assertEqual(result.decision.code, "TOOL_OUTPUT_INVALID")


if __name__ == "__main__":
    unittest.main()
