"""Security finding persistence boundary."""

from __future__ import annotations

from typing import Protocol

from app.security.models import SecurityFinding


class SecurityFindingRepository(Protocol):
    """Storage boundary for security findings."""

    async def create_many(self, findings: list[SecurityFinding]) -> None:
        """Persist findings."""

    async def list_by_target(self, project_id: str, target_type: str, target_id: str) -> list[SecurityFinding]:
        """Return findings for a target."""

    async def list_by_project(self, project_id: str) -> list[SecurityFinding]:
        """Return findings for a project."""


class InMemorySecurityFindingRepository:
    """Local security finding repository used by tests and early development."""

    def __init__(self) -> None:
        self._findings: list[SecurityFinding] = []

    async def create_many(self, findings: list[SecurityFinding]) -> None:
        self._findings.extend(findings)

    async def list_by_target(self, project_id: str, target_type: str, target_id: str) -> list[SecurityFinding]:
        return [
            finding
            for finding in self._findings
            if finding.project_id == project_id
            and finding.target_type == target_type
            and finding.target_id == target_id
        ]

    async def list_by_project(self, project_id: str) -> list[SecurityFinding]:
        return [
            finding
            for finding in self._findings
            if finding.project_id == project_id
        ]
