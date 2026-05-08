"""GCP Planner agent implementation."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any
from typing import Protocol

from app.architectures.models import parse_architecture_spec
from app.agents.runtime import AgentExecutionContext
from app.core.errors import ValidationAppError


class GcpPlannerGenerator(Protocol):
    """Boundary for LLM-backed GCP architecture planning."""

    async def generate(self, request: "GcpPlannerRequest") -> dict[str, Any]:
        """Return untrusted generated architecture output."""


@dataclass(frozen=True)
class GcpPlannerRequest:
    """Validated input passed to the GCP planner generator."""

    requirements_doc_md: str
    basic_design_md: str
    target_project_id: str


@dataclass(frozen=True)
class GcpPlannerOutput:
    """Validated GCP Planner output."""

    architecture_spec: dict[str, Any]
    rationale_md: str
    cloudbuild_yaml: str
    gcloud_commands: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "architecture_spec": dict(self.architecture_spec),
            "rationale_md": self.rationale_md,
            "cloudbuild_yaml": self.cloudbuild_yaml,
            "gcloud_commands": list(self.gcloud_commands),
        }


class GcpPlannerAgent:
    """Generate a validated GCP architecture proposal."""

    def __init__(self, generator: GcpPlannerGenerator) -> None:
        self._generator = generator

    async def run(self, context: AgentExecutionContext) -> dict[str, Any]:
        await context.progress(15, "validating planner input")
        request = _parse_planner_request(context.input_snapshot)

        read_decision = await context.request_tool(
            "read_document",
            {"doc_types": ["requirements", "basic_design"]},
        )
        if not read_decision.allowed:
            raise PermissionError(read_decision.message)

        await context.progress(25, "generating architecture proposal")
        generated_output = await self._generator.generate(request)
        if not isinstance(generated_output, Mapping):
            raise ValidationAppError("planner generator output must be an object")

        await context.progress(75, "validating architecture proposal")
        planner_output = _parse_planner_output(generated_output)

        estimate_decision = await context.request_tool(
            "estimate_cost",
            {"node_count": len(planner_output.architecture_spec["nodes"])},
        )
        if not estimate_decision.allowed:
            raise PermissionError(estimate_decision.message)

        write_decision = await context.request_tool(
            "write_architecture",
            {"target_project_id": request.target_project_id},
        )
        if not write_decision.allowed:
            raise PermissionError(write_decision.message)

        await context.progress(90, "architecture proposal ready")
        return planner_output.to_dict()


def _parse_planner_request(payload: Mapping[str, Any]) -> GcpPlannerRequest:
    requirements_doc_md = _required_string(payload, "requirements_doc_md")
    basic_design_md = _required_string(payload, "basic_design_md")
    target_project_id = _required_string(payload, "target_project_id")
    return GcpPlannerRequest(
        requirements_doc_md=requirements_doc_md,
        basic_design_md=basic_design_md,
        target_project_id=target_project_id,
    )


def _parse_planner_output(payload: Mapping[str, Any]) -> GcpPlannerOutput:
    architecture_spec = payload.get("architecture_spec")
    if not isinstance(architecture_spec, dict):
        raise ValidationAppError("architecture_spec must be an object")
    parse_architecture_spec(architecture_spec)

    rationale_md = _required_string(payload, "rationale_md")
    cloudbuild_yaml = _required_string(payload, "cloudbuild_yaml")
    gcloud_commands = payload.get("gcloud_commands")
    if not isinstance(gcloud_commands, list) or not gcloud_commands:
        raise ValidationAppError("gcloud_commands must be a non-empty list")
    normalized_commands: list[str] = []
    for command in gcloud_commands:
        if not isinstance(command, str) or not command.strip():
            raise ValidationAppError("gcloud_commands must contain only non-empty strings")
        normalized_commands.append(command.strip())

    return GcpPlannerOutput(
        architecture_spec=dict(architecture_spec),
        rationale_md=rationale_md,
        cloudbuild_yaml=cloudbuild_yaml,
        gcloud_commands=normalized_commands,
    )


def _required_string(payload: Mapping[str, Any], field_name: str) -> str:
    value = payload.get(field_name)
    if not isinstance(value, str) or not value.strip():
        raise ValidationAppError(f"{field_name} must be a non-empty string")
    return value.strip()
