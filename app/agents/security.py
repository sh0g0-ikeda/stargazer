"""Security agent implementation."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any
from typing import Protocol

from app.architectures.models import parse_architecture_spec
from app.agents.runtime import AgentExecutionContext
from app.core.errors import ValidationAppError
from app.security.models import SecuritySeverity


class SecurityEvaluator(Protocol):
    """Boundary for LLM-backed security evaluation."""

    async def evaluate(self, request: "SecurityEvaluationRequest") -> dict[str, Any]:
        """Return untrusted security evaluation output."""


@dataclass(frozen=True)
class SecurityEvaluationRequest:
    """Validated input passed to the security evaluator."""

    target_type: str
    target_id: str
    architecture_spec: dict[str, Any]


class SecurityAgent:
    """Evaluate architecture security findings."""

    def __init__(self, evaluator: SecurityEvaluator) -> None:
        self._evaluator = evaluator

    async def run(self, context: AgentExecutionContext) -> dict[str, Any]:
        await context.progress(15, "validating security input")
        request = _parse_security_request(context.input_snapshot)

        read_decision = await context.request_tool(
            "read_architecture",
            {"target_id": request.target_id},
        )
        if not read_decision.allowed:
            raise PermissionError(read_decision.message)

        await context.progress(35, "evaluating architecture security")
        generated_output = await self._evaluator.evaluate(request)
        if not isinstance(generated_output, Mapping):
            raise ValidationAppError("security evaluator output must be an object")

        await context.progress(80, "validating security findings")
        findings = _parse_findings(generated_output)

        write_decision = await context.request_tool(
            "write_security_findings",
            {"target_id": request.target_id},
        )
        if not write_decision.allowed:
            raise PermissionError(write_decision.message)

        await context.progress(90, "security findings ready")
        return {"findings": findings}


def _parse_security_request(payload: Mapping[str, Any]) -> SecurityEvaluationRequest:
    target_type = _required_string(payload, "target_type")
    target_id = _required_string(payload, "target_id")
    architecture_spec = payload.get("architecture_spec")
    if not isinstance(architecture_spec, dict):
        raise ValidationAppError("architecture_spec must be an object")
    parse_architecture_spec(architecture_spec)
    return SecurityEvaluationRequest(
        target_type=target_type,
        target_id=target_id,
        architecture_spec=dict(architecture_spec),
    )


def _parse_findings(payload: Mapping[str, Any]) -> list[dict[str, str]]:
    raw_findings = payload.get("findings", [])
    if not isinstance(raw_findings, list):
        raise ValidationAppError("findings must be a list")
    findings: list[dict[str, str]] = []
    for raw_finding in raw_findings:
        if not isinstance(raw_finding, dict):
            raise ValidationAppError("security finding must be an object")
        raw_severity = _required_string(raw_finding, "severity")
        try:
            severity = SecuritySeverity(raw_severity)
        except ValueError as exc:
            raise ValidationAppError("security finding severity is not supported", {"severity": raw_severity}) from exc
        findings.append(
            {
                "severity": severity.value,
                "category": _required_string(raw_finding, "category"),
                "message": _required_string(raw_finding, "message"),
                "suggestion": _required_string(raw_finding, "suggestion"),
            }
        )
    return findings


def _required_string(payload: Mapping[str, Any], field_name: str) -> str:
    value = payload.get(field_name)
    if not isinstance(value, str) or not value.strip():
        raise ValidationAppError(f"{field_name} must be a non-empty string")
    return value.strip()
