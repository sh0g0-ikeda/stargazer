"""Deterministic project phase orchestration."""

from __future__ import annotations

from collections.abc import Mapping


PHASE_TRANSITIONS: Mapping[str, frozenset[str]] = {
    "DRAFT": frozenset({"REQUIREMENT_DRAFT"}),
    "REQUIREMENT_DRAFT": frozenset({"REQUIREMENT_APPROVED"}),
    "REQUIREMENT_APPROVED": frozenset({"DESIGN_DRAFT"}),
    "DESIGN_DRAFT": frozenset({"DESIGN_APPROVED"}),
    "DESIGN_APPROVED": frozenset({"ARCHITECTURE_DRAFT"}),
    "ARCHITECTURE_DRAFT": frozenset({"SECURITY_REVIEW", "ARCHITECTURE_APPROVED"}),
    "SECURITY_REVIEW": frozenset({"ARCHITECTURE_DRAFT", "ARCHITECTURE_APPROVED"}),
    "ARCHITECTURE_APPROVED": frozenset({"READY_TO_APPLY"}),
    "READY_TO_APPLY": frozenset({"APPLYING"}),
    "APPLYING": frozenset({"DEPLOYED", "APPLY_FAILED"}),
    "APPLY_FAILED": frozenset({"ARCHITECTURE_DRAFT", "READY_TO_APPLY"}),
    "DEPLOYED": frozenset(),
}


class PhaseConflictError(ValueError):
    """Raised when a requested project phase transition is invalid."""


class ProjectOrchestrator:
    """Small deterministic state machine for project phase transitions."""

    def __init__(self, transitions: Mapping[str, frozenset[str]] | None = None) -> None:
        self._transitions = transitions or PHASE_TRANSITIONS

    def next_phases(self, current_phase: str) -> frozenset[str]:
        try:
            return self._transitions[current_phase]
        except KeyError as exc:
            raise PhaseConflictError(f"unknown project phase: {current_phase}") from exc

    def validate_transition(self, current_phase: str, next_phase: str) -> None:
        allowed_next_phases = self.next_phases(current_phase)
        if next_phase not in allowed_next_phases:
            raise PhaseConflictError(
                f"cannot transition from {current_phase} to {next_phase}"
            )
