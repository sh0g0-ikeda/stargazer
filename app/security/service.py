"""Security finding application service."""

from __future__ import annotations

from typing import Any

from app.core.errors import ValidationAppError
from app.security.models import SecurityFinding
from app.security.models import SecuritySeverity
from app.security.repository import SecurityFindingRepository


class SecurityFindingService:
    """Validate and persist security findings."""

    def __init__(self, repository: SecurityFindingRepository) -> None:
        self._repository = repository

    async def create_findings(
        self,
        *,
        project_id: str,
        target_type: str,
        target_id: str,
        finding_payloads: list[dict[str, Any]],
    ) -> list[SecurityFinding]:
        findings = [
            _parse_finding(
                project_id=project_id,
                target_type=target_type,
                target_id=target_id,
                payload=payload,
            )
            for payload in finding_payloads
        ]
        await self._repository.create_many(findings)
        return findings

    async def list_by_target(self, project_id: str, target_type: str, target_id: str) -> list[SecurityFinding]:
        return await self._repository.list_by_target(project_id, target_type, target_id)


def _parse_finding(
    *,
    project_id: str,
    target_type: str,
    target_id: str,
    payload: dict[str, Any],
) -> SecurityFinding:
    raw_severity = payload.get("severity")
    if not isinstance(raw_severity, str):
        raise ValidationAppError("security finding severity must be a string")
    try:
        severity = SecuritySeverity(raw_severity)
    except ValueError as exc:
        raise ValidationAppError("security finding severity is not supported", {"severity": raw_severity}) from exc

    return SecurityFinding.create(
        project_id=project_id,
        target_type=target_type,
        target_id=target_id,
        severity=severity,
        category=_required_string(payload, "category"),
        message=_required_string(payload, "message"),
        suggestion=_required_string(payload, "suggestion"),
    )


def _required_string(payload: dict[str, Any], field_name: str) -> str:
    value = payload.get(field_name)
    if not isinstance(value, str) or not value.strip():
        raise ValidationAppError(f"{field_name} must be a non-empty string")
    return value.strip()
