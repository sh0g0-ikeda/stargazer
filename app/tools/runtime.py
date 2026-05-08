"""Runtime for executing approved agent tools."""

from __future__ import annotations

from collections.abc import Awaitable
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from app.agents.schemas import AgentRole
from app.agents.schemas import ToolDecision
from app.agents.schemas import ToolRequest
from app.agents.tool_guard import ToolGuard
from app.agents.tool_guard import ToolPolicyContext

ToolHandler = Callable[[dict[str, Any]], Awaitable[dict[str, Any]]]


@dataclass(frozen=True)
class ToolExecutionContext:
    """Context needed to execute a tool request."""

    role: AgentRole
    project_phase: str
    approved_tool_names: frozenset[str]


@dataclass(frozen=True)
class ToolExecutionResult:
    """Result from one tool execution attempt."""

    decision: ToolDecision
    output: dict[str, Any] | None


class ToolRuntime:
    """Execute registered tool handlers only after policy approval."""

    def __init__(self, *, tool_guard: ToolGuard, handlers: dict[str, ToolHandler]) -> None:
        self._tool_guard = tool_guard
        self._handlers = dict(handlers)

    async def execute(
        self,
        *,
        request: ToolRequest,
        context: ToolExecutionContext,
    ) -> ToolExecutionResult:
        decision = self._tool_guard.evaluate(
            role=context.role,
            request=request,
            context=ToolPolicyContext(
                project_phase=context.project_phase,
                approved_tool_names=context.approved_tool_names,
            ),
        )
        if not decision.allowed:
            return ToolExecutionResult(decision=decision, output=None)

        handler = self._handlers.get(request.tool_name)
        if handler is None:
            return ToolExecutionResult(
                decision=ToolDecision(
                    allowed=False,
                    code="TOOL_HANDLER_NOT_FOUND",
                    message=f"tool handler is not registered: {request.tool_name}",
                ),
                output=None,
            )

        output = await handler(dict(request.arguments))
        if not isinstance(output, dict):
            return ToolExecutionResult(
                decision=ToolDecision(
                    allowed=False,
                    code="TOOL_OUTPUT_INVALID",
                    message=f"tool handler returned invalid output: {request.tool_name}",
                ),
                output=None,
            )
        return ToolExecutionResult(decision=decision, output=output)
