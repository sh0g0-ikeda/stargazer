"""Ops Dashboard aggregation service."""

from __future__ import annotations

from typing import Any

from app.architectures.service import ArchitectureService
from app.core.errors import AppError
from app.deployments.service import DeploymentService
from app.projects.service import ProjectService
from app.security.models import SecuritySeverity
from app.security.service import SecurityFindingService
from app.timeline.service import TimelineService


class OpsDashboardService:
    """Build the eight MVP Ops Dashboard sections from application state."""

    def __init__(
        self,
        *,
        project_service: ProjectService,
        architecture_service: ArchitectureService,
        deployment_service: DeploymentService,
        finding_service: SecurityFindingService,
        timeline_service: TimelineService,
    ) -> None:
        self._project_service = project_service
        self._architecture_service = architecture_service
        self._deployment_service = deployment_service
        self._finding_service = finding_service
        self._timeline_service = timeline_service

    async def overview(self, *, project_id: str) -> dict[str, Any]:
        project = await self._project_service.get_project_payload(project_id)
        architecture = await _optional_payload(self._architecture_service.latest_payload(project_id))
        deployment = await _optional_payload(self._deployment_service.latest_payload(project_id))
        findings = await self._finding_service.list_by_project(project_id)
        timeline = await self._timeline_service.list_payloads(project_id)
        return {
            "system_overview": {
                "project_id": project["id"],
                "phase": project["phase"],
                "health": "deployed" if project["phase"] == "DEPLOYED" else "in_progress",
            },
            "architecture_map": architecture["spec"] if architecture else None,
            "deployment_status": deployment,
            "logs_errors": {
                "items": [],
                "summary": "Cloud Logging adapter is not configured in demo mode.",
            },
            "cost_overview": _estimate_cost(architecture),
            "security_overview": _security_summary(findings),
            "agent_actions": timeline,
            "recommended_next_actions": _next_actions(project["phase"], findings),
        }


async def _optional_payload(awaitable: Any) -> dict[str, Any] | None:
    try:
        return await awaitable
    except AppError:
        return None


def _estimate_cost(architecture: dict[str, Any] | None) -> dict[str, Any]:
    if architecture is None:
        return {"monthly_jpy": 0, "items": []}
    items = []
    monthly_jpy = 0
    for node in architecture["spec"]["nodes"]:
        estimate = _node_cost(node["type"])
        monthly_jpy += estimate
        items.append(
            {
                "node_id": node["id"],
                "node_type": node["type"],
                "monthly_jpy": estimate,
            }
        )
    return {"monthly_jpy": monthly_jpy, "items": items}


def _node_cost(node_type: str) -> int:
    estimates = {
        "cloud_run": 800,
        "firestore": 400,
        "secret_manager": 100,
        "cloud_storage": 200,
        "cloud_logging": 200,
        "cloud_monitoring": 200,
        "artifact_registry": 300,
        "iam_sa": 0,
        "external": 0,
    }
    return estimates.get(node_type, 0)


def _security_summary(findings: list[Any]) -> dict[str, Any]:
    counts = {
        SecuritySeverity.CRITICAL.value: 0,
        SecuritySeverity.WARNING.value: 0,
        SecuritySeverity.INFO.value: 0,
    }
    for finding in findings:
        counts[finding.severity.value] += 1
    return {
        "counts": counts,
        "findings": [
            {
                "id": finding.id,
                "severity": finding.severity.value,
                "category": finding.category,
                "message": finding.message,
                "suggestion": finding.suggestion,
            }
            for finding in findings
        ],
    }


def _next_actions(project_phase: str, findings: list[Any]) -> list[dict[str, str]]:
    if any(finding.severity is SecuritySeverity.CRITICAL for finding in findings):
        return [
            {
                "priority": "high",
                "title": "Critical findings を解消する",
                "rationale": "構成適用前に重大なセキュリティ指摘を解消してください。",
            }
        ]
    actions_by_phase = {
        "DRAFT": "要件入力を開始する",
        "REQUIREMENT_DRAFT": "要件定義書を承認する",
        "REQUIREMENT_APPROVED": "設計書を生成する",
        "DESIGN_DRAFT": "設計書を承認する",
        "DESIGN_APPROVED": "GCP構成案を生成する",
        "ARCHITECTURE_DRAFT": "セキュリティ評価を確認して構成を承認する",
        "ARCHITECTURE_APPROVED": "構成をApplyする",
        "READY_TO_APPLY": "Cloud Buildを起動する",
        "DEPLOYED": "デモURLとダッシュボードを確認する",
    }
    return [
        {
            "priority": "normal",
            "title": actions_by_phase.get(project_phase, "状態を確認する"),
            "rationale": "現在のフェーズから次に進むための推奨操作です。",
        }
    ]
