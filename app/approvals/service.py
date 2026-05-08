"""Approval application service."""

from __future__ import annotations

from typing import Any

from app.approvals.models import ApprovalDecision
from app.approvals.models import ApprovalGate
from app.approvals.models import ApprovalRecord
from app.approvals.repository import ApprovalRepository
from app.core.errors import ValidationAppError
from app.projects.models import ProjectPhase
from app.projects.service import ProjectService


APPROVED_PHASE_BY_GATE = {
    ApprovalGate.REQUIREMENTS: ProjectPhase.REQUIREMENT_APPROVED,
    ApprovalGate.DESIGN: ProjectPhase.DESIGN_APPROVED,
    ApprovalGate.ARCHITECTURE: ProjectPhase.ARCHITECTURE_APPROVED,
    ApprovalGate.TARGET_APP: ProjectPhase.READY_TO_APPLY,
}


class ApprovalService:
    """Record approval decisions and advance project phases when approved."""

    def __init__(
        self,
        *,
        repository: ApprovalRepository,
        project_service: ProjectService,
    ) -> None:
        self._repository = repository
        self._project_service = project_service

    async def decide(
        self,
        *,
        project_id: str,
        gate: ApprovalGate,
        decision: ApprovalDecision,
        decided_by: str,
        rationale: str = "",
        snapshot: dict[str, Any] | None = None,
    ) -> ApprovalRecord:
        approval = ApprovalRecord.create(
            project_id=project_id,
            gate=gate,
            decision=decision,
            decided_by=decided_by,
            rationale=rationale,
            snapshot=snapshot,
        )
        if decision is ApprovalDecision.APPROVED:
            await self._project_service.transition_project(
                project_id=project_id,
                next_phase=APPROVED_PHASE_BY_GATE[gate],
            )
        await self._repository.create(approval)
        return approval

    async def list_payloads(self, project_id: str) -> list[dict[str, Any]]:
        approvals = await self._repository.list_by_project(project_id)
        return [_approval_payload(approval) for approval in approvals]


def parse_approval_gate(raw_gate: str) -> ApprovalGate:
    try:
        return ApprovalGate(raw_gate)
    except ValueError as exc:
        raise ValidationAppError("approval gate is not supported", {"gate": raw_gate}) from exc


def parse_approval_decision(raw_decision: str) -> ApprovalDecision:
    try:
        return ApprovalDecision(raw_decision)
    except ValueError as exc:
        raise ValidationAppError(
            "approval decision is not supported",
            {"decision": raw_decision},
        ) from exc


def _approval_payload(approval: ApprovalRecord) -> dict[str, Any]:
    return {
        "id": approval.id,
        "project_id": approval.project_id,
        "gate": approval.gate.value,
        "decision": approval.decision.value,
        "decided_by": approval.decided_by,
        "rationale": approval.rationale,
        "snapshot": dict(approval.snapshot),
        "created_at": approval.created_at.isoformat(),
    }
