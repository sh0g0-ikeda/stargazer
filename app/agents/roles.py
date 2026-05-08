"""Built-in agent role definitions."""

from __future__ import annotations

from app.agents.schemas import AgentRole


REQUIREMENT_AGENT = AgentRole(
    name="requirement_agent",
    model="gemini-3.1-pro-preview",
    thinking_level="medium",
    allowed_tools=frozenset(
        {
            "read_project",
            "write_document",
            "write_timeline_event",
        }
    ),
)

ARCHITECT_AGENT = AgentRole(
    name="architect_agent",
    model="gemini-3.1-pro-preview",
    thinking_level="high",
    allowed_tools=frozenset(
        {
            "read_project",
            "read_document",
            "write_document",
            "write_timeline_event",
        }
    ),
)

GCP_PLANNER_AGENT = AgentRole(
    name="gcp_planner_agent",
    model="gemini-3.1-pro-preview",
    thinking_level="high",
    allowed_tools=frozenset(
        {
            "read_project",
            "read_document",
            "write_architecture",
            "estimate_cost",
            "write_timeline_event",
        }
    ),
)

SECURITY_AGENT = AgentRole(
    name="security_agent",
    model="gemini-3.1-pro-preview",
    thinking_level="high",
    allowed_tools=frozenset(
        {
            "read_project",
            "read_document",
            "read_architecture",
            "write_security_findings",
            "write_timeline_event",
        }
    ),
)


BUILT_IN_ROLES: dict[str, AgentRole] = {
    role.name: role
    for role in (
        REQUIREMENT_AGENT,
        ARCHITECT_AGENT,
        GCP_PLANNER_AGENT,
        SECURITY_AGENT,
    )
}


def get_role(role_name: str) -> AgentRole:
    """Return a built-in role by name."""

    try:
        return BUILT_IN_ROLES[role_name]
    except KeyError as exc:
        raise ValueError(f"unknown agent role: {role_name}") from exc
