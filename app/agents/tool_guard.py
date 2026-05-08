"""Policy checks for agent tool requests."""

from __future__ import annotations

from dataclasses import dataclass

from app.agents.schemas import AgentRole
from app.agents.schemas import ToolDecision
from app.agents.schemas import ToolDefinition
from app.agents.schemas import ToolRequest
from app.agents.schemas import ToolRisk


@dataclass(frozen=True)
class ToolPolicyContext:
    """Runtime context required to evaluate a tool request."""

    project_phase: str
    approved_tool_names: frozenset[str]


class ToolGuard:
    """Validate whether an agent may execute a requested tool."""

    def __init__(self, tools: list[ToolDefinition]) -> None:
        self._tools = {tool.name: tool for tool in tools}

    def evaluate(
        self,
        *,
        role: AgentRole,
        request: ToolRequest,
        context: ToolPolicyContext,
    ) -> ToolDecision:
        tool = self._tools.get(request.tool_name)
        if tool is None:
            return ToolDecision(
                allowed=False,
                code="TOOL_NOT_FOUND",
                message=f"tool is not registered: {request.tool_name}",
            )

        if request.tool_name not in role.allowed_tools:
            return ToolDecision(
                allowed=False,
                code="TOOL_NOT_ALLOWED_FOR_ROLE",
                message=f"tool is not allowed for role: {role.name}",
            )

        if context.project_phase not in tool.allowed_phases:
            return ToolDecision(
                allowed=False,
                code="TOOL_NOT_ALLOWED_IN_PHASE",
                message=f"tool is not allowed in phase: {context.project_phase}",
            )

        requires_approval = tool.requires_approval or tool.risk is ToolRisk.DESTRUCTIVE
        if requires_approval and request.tool_name not in context.approved_tool_names:
            return ToolDecision(
                allowed=False,
                code="APPROVAL_REQUIRED",
                message=f"tool requires approval: {request.tool_name}",
                requires_approval=True,
            )

        return ToolDecision(
            allowed=True,
            code="TOOL_ALLOWED",
            message="tool request allowed",
        )


DEFAULT_TOOL_DEFINITIONS = [
    ToolDefinition(
        name="read_project",
        risk=ToolRisk.READ_ONLY,
        allowed_phases=frozenset({"REQUIREMENT_DRAFT", "DESIGN_DRAFT", "ARCHITECTURE_DRAFT"}),
    ),
    ToolDefinition(
        name="read_document",
        risk=ToolRisk.READ_ONLY,
        allowed_phases=frozenset({"DESIGN_DRAFT", "ARCHITECTURE_DRAFT"}),
    ),
    ToolDefinition(
        name="read_architecture",
        risk=ToolRisk.READ_ONLY,
        allowed_phases=frozenset({"ARCHITECTURE_DRAFT", "SECURITY_REVIEW"}),
    ),
    ToolDefinition(
        name="write_document",
        risk=ToolRisk.WRITE,
        allowed_phases=frozenset({"REQUIREMENT_DRAFT", "DESIGN_DRAFT"}),
    ),
    ToolDefinition(
        name="write_architecture",
        risk=ToolRisk.WRITE,
        allowed_phases=frozenset({"ARCHITECTURE_DRAFT"}),
    ),
    ToolDefinition(
        name="write_security_findings",
        risk=ToolRisk.WRITE,
        allowed_phases=frozenset({"SECURITY_REVIEW", "ARCHITECTURE_DRAFT"}),
    ),
    ToolDefinition(
        name="write_timeline_event",
        risk=ToolRisk.WRITE,
        allowed_phases=frozenset(
            {
                "REQUIREMENT_DRAFT",
                "DESIGN_DRAFT",
                "ARCHITECTURE_DRAFT",
                "SECURITY_REVIEW",
                "READY_TO_APPLY",
            }
        ),
    ),
    ToolDefinition(
        name="estimate_cost",
        risk=ToolRisk.READ_ONLY,
        allowed_phases=frozenset({"ARCHITECTURE_DRAFT"}),
    ),
    ToolDefinition(
        name="trigger_cloud_build",
        risk=ToolRisk.DESTRUCTIVE,
        allowed_phases=frozenset({"READY_TO_APPLY"}),
        requires_approval=True,
    ),
]
