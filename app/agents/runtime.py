"""Execution runtime for CastorOps agents."""

from __future__ import annotations

from collections.abc import Awaitable
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Protocol

from app.agents.schemas import AgentEvent
from app.agents.schemas import AgentEventType
from app.agents.schemas import AgentRole
from app.agents.schemas import AgentRun
from app.agents.schemas import AgentRunStatus
from app.agents.schemas import ProgressUpdate
from app.agents.schemas import ToolDecision
from app.agents.schemas import ToolRequest
from app.agents.schemas import utc_now
from app.agents.tool_guard import ToolGuard
from app.agents.tool_guard import ToolPolicyContext


class Agent(Protocol):
    """Protocol implemented by concrete role agents."""

    async def run(self, context: "AgentExecutionContext") -> dict[str, Any]:
        """Execute the agent and return structured output."""


class AgentStore(Protocol):
    """Persistence boundary for runtime state."""

    async def create_run(self, run: AgentRun) -> None:
        """Persist a new agent run."""

    async def update_run(self, run: AgentRun) -> None:
        """Persist the latest run state."""

    async def append_event(self, event: AgentEvent) -> None:
        """Persist an ordered run event."""


@dataclass(frozen=True)
class RuntimeLimits:
    """Limits that prevent accidental runaway agent execution."""

    max_parallel_agents: int = 2
    max_agent_depth: int = 1

    def __post_init__(self) -> None:
        if self.max_parallel_agents <= 0:
            raise ValueError("max_parallel_agents must be positive")
        if self.max_agent_depth < 0:
            raise ValueError("max_agent_depth must not be negative")


class InMemoryAgentStore:
    """Small test/local store for agent runtime state."""

    def __init__(self) -> None:
        self.runs: dict[str, AgentRun] = {}
        self.events: dict[str, list[AgentEvent]] = {}

    async def create_run(self, run: AgentRun) -> None:
        self.runs[run.id] = run
        self.events[run.id] = []

    async def update_run(self, run: AgentRun) -> None:
        self.runs[run.id] = run

    async def append_event(self, event: AgentEvent) -> None:
        self.events.setdefault(event.run_id, []).append(event)


class AgentExecutionContext:
    """Operations exposed to an agent during one run."""

    def __init__(
        self,
        *,
        run: AgentRun,
        role: AgentRole,
        input_snapshot: dict[str, Any],
        emit_progress: Callable[[ProgressUpdate], Awaitable[None]],
        request_tool: Callable[[ToolRequest], Awaitable[ToolDecision]],
    ) -> None:
        self.run = run
        self.role = role
        self.input_snapshot = input_snapshot
        self._emit_progress = emit_progress
        self._request_tool = request_tool

    async def progress(self, percent: int, label: str) -> None:
        await self._emit_progress(ProgressUpdate(percent=percent, label=label))

    async def request_tool(self, tool_name: str, arguments: dict[str, Any]) -> ToolDecision:
        return await self._request_tool(ToolRequest(tool_name=tool_name, arguments=arguments))


class AgentRuntime:
    """Run agents with ordered events, monotonic progress, and tool policy checks."""

    def __init__(
        self,
        *,
        store: AgentStore,
        tool_guard: ToolGuard,
        limits: RuntimeLimits | None = None,
    ) -> None:
        self._store = store
        self._tool_guard = tool_guard
        self._limits = limits or RuntimeLimits()
        self._active_run_ids: set[str] = set()

    async def run_agent(
        self,
        *,
        project_id: str,
        project_phase: str,
        role: AgentRole,
        agent_path: str,
        agent: Agent,
        input_snapshot: dict[str, Any],
        approved_tool_names: frozenset[str] = frozenset(),
        parent_run_id: str | None = None,
    ) -> AgentRun:
        self._validate_agent_path(agent_path)
        self._enforce_limits(agent_path)

        run = AgentRun.create(
            project_id=project_id,
            role=role,
            agent_path=agent_path,
            input_snapshot=input_snapshot,
            parent_run_id=parent_run_id,
        )
        await self._store.create_run(run)
        seq = 0

        async def emit_event(event_type: AgentEventType, payload: dict[str, Any] | None = None) -> None:
            nonlocal seq
            seq += 1
            await self._store.append_event(
                AgentEvent.create(
                    run_id=run.id,
                    agent_path=run.agent_path,
                    seq=seq,
                    event_type=event_type,
                    payload=payload,
                )
            )

        async def emit_progress(update: ProgressUpdate) -> None:
            if update.percent < run.progress_percent:
                raise ValueError("progress percent must be monotonic")
            run.progress_percent = update.percent
            run.progress_label = update.label
            await emit_event(
                AgentEventType.PROGRESS,
                {"percent": update.percent, "label": update.label},
            )
            await self._store.update_run(run)

        async def request_tool(request: ToolRequest) -> ToolDecision:
            await emit_event(
                AgentEventType.TOOL_REQUESTED,
                {"tool_name": request.tool_name},
            )
            decision = self._tool_guard.evaluate(
                role=role,
                request=request,
                context=ToolPolicyContext(
                    project_phase=project_phase,
                    approved_tool_names=approved_tool_names,
                ),
            )
            if decision.requires_approval:
                run.status = AgentRunStatus.WAITING_APPROVAL
                run.error_code = decision.code
                run.error_message = decision.message
                await emit_event(AgentEventType.APPROVAL_REQUIRED, {"tool_name": request.tool_name})
                await self._store.update_run(run)
            await emit_event(
                AgentEventType.TOOL_FINISHED,
                {
                    "tool_name": request.tool_name,
                    "allowed": decision.allowed,
                    "code": decision.code,
                },
            )
            return decision

        self._active_run_ids.add(run.id)
        try:
            await emit_event(AgentEventType.RUN_CREATED, {"agent_name": role.name})
            run.status = AgentRunStatus.RUNNING
            run.started_at = utc_now()
            await emit_event(AgentEventType.RUN_STARTED, {"agent_name": role.name})
            await emit_progress(ProgressUpdate(percent=5, label="run created"))

            context = AgentExecutionContext(
                run=run,
                role=role,
                input_snapshot=dict(input_snapshot),
                emit_progress=emit_progress,
                request_tool=request_tool,
            )
            output = await agent.run(context)

            if run.status is AgentRunStatus.WAITING_APPROVAL:
                run.finished_at = utc_now()
                await self._store.update_run(run)
                return run

            run.output = output
            run.status = AgentRunStatus.SUCCEEDED
            await emit_progress(ProgressUpdate(percent=100, label="run completed"))
            run.finished_at = utc_now()
            await emit_event(AgentEventType.RUN_SUCCEEDED, {"output_keys": sorted(output.keys())})
            await self._store.update_run(run)
            return run
        except Exception as exc:
            run.status = AgentRunStatus.FAILED
            run.error_code = exc.__class__.__name__
            run.error_message = str(exc)
            run.finished_at = utc_now()
            await emit_event(
                AgentEventType.RUN_FAILED,
                {"error_code": run.error_code, "message": run.error_message},
            )
            await self._store.update_run(run)
            return run
        finally:
            self._active_run_ids.discard(run.id)

    def _enforce_limits(self, agent_path: str) -> None:
        if len(self._active_run_ids) >= self._limits.max_parallel_agents:
            raise RuntimeError("max_parallel_agents limit reached")

        depth = self._agent_depth(agent_path)
        if depth > self._limits.max_agent_depth:
            raise RuntimeError("max_agent_depth limit reached")

    @staticmethod
    def _validate_agent_path(agent_path: str) -> None:
        if agent_path == "/root":
            return
        if not agent_path.startswith("/root/"):
            raise ValueError("agent_path must start with /root")
        for segment in agent_path.removeprefix("/root/").split("/"):
            if not segment or segment in {".", "..", "root"}:
                raise ValueError("agent_path contains an invalid segment")
            if not all(ch.islower() or ch.isdigit() or ch == "_" for ch in segment):
                raise ValueError("agent_path segments must use lowercase letters, digits, or _")

    @staticmethod
    def _agent_depth(agent_path: str) -> int:
        if agent_path == "/root":
            return 0
        return len(agent_path.removeprefix("/root/").split("/"))
