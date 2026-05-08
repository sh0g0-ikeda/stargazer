"""Approval persistence boundary."""

from __future__ import annotations

from typing import Protocol

from app.approvals.models import ApprovalRecord


class ApprovalRepository(Protocol):
    """Storage boundary for approval records."""

    async def create(self, approval: ApprovalRecord) -> None:
        """Persist an approval record."""

    async def list_by_project(self, project_id: str) -> list[ApprovalRecord]:
        """Return approval history for one project."""


class InMemoryApprovalRepository:
    """Local approval repository used by tests and demo mode."""

    def __init__(self) -> None:
        self._approvals: list[ApprovalRecord] = []

    async def create(self, approval: ApprovalRecord) -> None:
        self._approvals.append(approval)

    async def list_by_project(self, project_id: str) -> list[ApprovalRecord]:
        return [
            approval
            for approval in sorted(self._approvals, key=lambda item: item.created_at)
            if approval.project_id == project_id
        ]
