import unittest

from app.agents.roles import REQUIREMENT_AGENT
from app.agents.runtime import AgentExecutionContext
from app.agents.runtime import AgentRuntime
from app.agents.runtime import InMemoryAgentStore
from app.agents.runtime import RuntimeLimits
from app.agents.schemas import AgentRunStatus
from app.agents.schemas import AgentRole
from app.agents.schemas import ToolDecision
from app.agents.schemas import derive_status_from_events
from app.agents.tool_guard import DEFAULT_TOOL_DEFINITIONS
from app.agents.tool_guard import ToolGuard


class SuccessfulRequirementAgent:
    async def run(self, context: AgentExecutionContext) -> dict[str, str]:
        await context.progress(15, "input validated")
        decision = await context.request_tool("write_document", {"doc_type": "requirements"})
        if not decision.allowed:
            raise RuntimeError(decision.message)
        await context.progress(75, "document generated")
        return {"document_id": "requirements-v1"}


class ApprovalRequestingAgent:
    async def run(self, context: AgentExecutionContext) -> dict[str, str]:
        decision: ToolDecision = await context.request_tool("trigger_cloud_build", {})
        if not decision.allowed:
            return {"blocked_by": decision.code}
        return {"build_id": "build-123"}


class RegressingProgressAgent:
    async def run(self, context: AgentExecutionContext) -> dict[str, str]:
        await context.progress(30, "started")
        await context.progress(20, "went backwards")
        return {"status": "unreachable"}


class AgentRuntimeTests(unittest.IsolatedAsyncioTestCase):
    async def test_successful_run_records_events_and_reaches_100_percent(self) -> None:
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
            agent=SuccessfulRequirementAgent(),
            input_snapshot={"idea": "help desk"},
        )

        self.assertEqual(run.status, AgentRunStatus.SUCCEEDED)
        self.assertEqual(derive_status_from_events(store.events[run.id]), AgentRunStatus.SUCCEEDED)
        self.assertEqual(run.progress_percent, 100)
        self.assertEqual(run.output, {"document_id": "requirements-v1"})
        self.assertGreaterEqual(len(store.events[run.id]), 6)
        self.assertEqual([event.seq for event in store.events[run.id]], list(range(1, len(store.events[run.id]) + 1)))

    async def test_destructive_tool_requires_approval(self) -> None:
        store = InMemoryAgentStore()
        runtime = AgentRuntime(
            store=store,
            tool_guard=ToolGuard(DEFAULT_TOOL_DEFINITIONS),
        )
        apply_role = AgentRole(
            name="apply_agent",
            model="gemini-3.1-pro-preview",
            thinking_level="medium",
            allowed_tools=frozenset({"trigger_cloud_build"}),
        )

        run = await runtime.run_agent(
            project_id="project-1",
            project_phase="READY_TO_APPLY",
            role=apply_role,
            agent_path="/root/apply_agent",
            agent=ApprovalRequestingAgent(),
            input_snapshot={"architecture_id": "arch-1"},
        )

        self.assertEqual(run.status, AgentRunStatus.WAITING_APPROVAL)
        self.assertEqual(
            derive_status_from_events(store.events[run.id]),
            AgentRunStatus.WAITING_APPROVAL,
        )
        self.assertEqual(run.error_code, "APPROVAL_REQUIRED")
        event_types = [event.event_type.value for event in store.events[run.id]]
        self.assertIn("APPROVAL_REQUIRED", event_types)

    async def test_progress_cannot_move_backwards(self) -> None:
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
            agent=RegressingProgressAgent(),
            input_snapshot={"idea": "help desk"},
        )

        self.assertEqual(run.status, AgentRunStatus.FAILED)
        self.assertEqual(run.error_code, "ValueError")

    async def test_agent_path_depth_limit_is_enforced(self) -> None:
        store = InMemoryAgentStore()
        runtime = AgentRuntime(
            store=store,
            tool_guard=ToolGuard(DEFAULT_TOOL_DEFINITIONS),
            limits=RuntimeLimits(max_agent_depth=1),
        )

        with self.assertRaises(RuntimeError):
            await runtime.run_agent(
                project_id="project-1",
                project_phase="REQUIREMENT_DRAFT",
                role=REQUIREMENT_AGENT,
                agent_path="/root/requirement_agent/child",
                agent=SuccessfulRequirementAgent(),
                input_snapshot={"idea": "help desk"},
            )


if __name__ == "__main__":
    unittest.main()
