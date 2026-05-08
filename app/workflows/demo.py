"""Local demo helpers for exercising workflows without cloud dependencies."""

from __future__ import annotations

from typing import Any

from app.agents.requirement import RequirementGenerationRequest
from app.agents.architect import ArchitectGenerationRequest
from app.agents.gcp_planner import GcpPlannerRequest
from app.agents.runtime import AgentRuntime
from app.agents.runtime import InMemoryAgentStore
from app.agents.schemas import AgentRunStatus
from app.agents.security import SecurityEvaluationRequest
from app.agents.tool_guard import DEFAULT_TOOL_DEFINITIONS
from app.agents.tool_guard import ToolGuard
from app.api.responses import ApiResponse
from app.architectures.repository import InMemoryArchitectureRepository
from app.architectures.service import ArchitectureService
from app.documents.models import DocumentType
from app.documents.repository import InMemoryDocumentRepository
from app.documents.service import DocumentService
from app.projects.models import ProjectPhase
from app.projects.repository import InMemoryProjectRepository
from app.projects.service import ProjectService
from app.security.repository import InMemorySecurityFindingRepository
from app.security.service import SecurityFindingService
from app.workflows.designs import DesignWorkflowService
from app.workflows.planning import PlanningWorkflowService
from app.workflows.requirements import RequirementWorkflowService
from app.workflows.security import SecurityEvaluationWorkflowService


class DemoRequirementGenerator:
    """Deterministic requirement generator used for local smoke tests."""

    async def generate(self, request: RequirementGenerationRequest) -> dict[str, Any]:
        unresolved_items = []
        follow_up_questions = []
        if "auth" not in request.follow_up_answers:
            unresolved_items.append("認証方式")
            follow_up_questions.append("ログイン機能は必要ですか。必要な場合は方式も教えてください。")
        if not request.form_responses.get("data_storage"):
            follow_up_questions.append("保存したいデータの種類と保持期間を教えてください。")
        if not request.form_responses.get("public_scope"):
            follow_up_questions.append("公開範囲は社内限定、招待制、一般公開のどれを想定していますか。")

        return {
            "follow_up_questions": follow_up_questions[:3],
            "requirements_doc_md": _build_requirements_doc(request, unresolved_items),
            "unresolved_items": unresolved_items,
        }


class DemoArchitectGenerator:
    """Deterministic architect generator used for local smoke tests."""

    async def generate(self, request: ArchitectGenerationRequest) -> dict[str, Any]:
        title_by_type = {
            DocumentType.BASIC_DESIGN: "基本設計書",
            DocumentType.API_DESIGN: "API設計書",
            DocumentType.DATA_DESIGN: "データ設計書",
            DocumentType.OPS_DESIGN: "運用設計書",
            DocumentType.SECURITY_DESIGN: "セキュリティ設計書",
            DocumentType.ADR: "ADR",
            DocumentType.TASKS: "実装タスク",
        }
        title = title_by_type[request.doc_type]
        return {
            "doc_md": f"# {title}\n\n## 1. 概要\n{request.requirements_doc_md[:120]}",
            "references": ["requirements:latest"],
        }


class DemoGcpPlannerGenerator:
    """Deterministic GCP planner used for local smoke tests."""

    async def generate(self, request: GcpPlannerRequest) -> dict[str, Any]:
        return {
            "architecture_spec": {
                "project_id": request.target_project_id,
                "region": "asia-northeast1",
                "nodes": [
                    {
                        "id": "backend",
                        "type": "cloud_run",
                        "name": "Star Gazer Backend",
                        "parameters": {"memory": "512Mi", "cpu": "1"},
                        "rationale": "FastAPI backendをCloud Runで公開する",
                        "cost_band": "low",
                        "security_notes": ["認証必須", "最小権限のサービスアカウントを使う"],
                    },
                    {
                        "id": "firestore",
                        "type": "firestore",
                        "name": "Project State Store",
                        "parameters": {"mode": "native"},
                        "rationale": "プロジェクト状態と履歴を保存する",
                        "cost_band": "low",
                    },
                ],
                "edges": [
                    {
                        "id": "backend-firestore",
                        "from_node": "backend",
                        "to_node": "firestore",
                        "type": "db_rw",
                        "description": "Backend reads and writes project state.",
                    }
                ],
            },
            "rationale_md": "Cloud Run + Firestore のMVP構成を採用する。",
            "cloudbuild_yaml": "steps: []",
            "gcloud_commands": ["gcloud run services list"],
        }


class DemoSecurityEvaluator:
    """Deterministic security evaluator used for local smoke tests."""

    async def evaluate(self, request: SecurityEvaluationRequest) -> dict[str, Any]:
        return {
            "findings": [
                {
                    "severity": "warning",
                    "category": "iam",
                    "message": "サービスアカウント権限は実デプロイ前に絞り込む必要がある。",
                    "suggestion": "Cloud Build SA と Backend SA を分離し、必要権限のみ付与する。",
                }
            ]
        }


async def build_requirement_demo_response(*, idea: str, owner_uid: str) -> ApiResponse:
    """Run the requirement workflow locally and return the API response envelope."""

    project_repository = InMemoryProjectRepository()
    project_service = ProjectService(repository=project_repository)
    document_service = DocumentService(InMemoryDocumentRepository())
    workflow = RequirementWorkflowService(
        project_service=project_service,
        document_service=document_service,
        agent_runtime=AgentRuntime(
            store=InMemoryAgentStore(),
            tool_guard=ToolGuard(DEFAULT_TOOL_DEFINITIONS),
        ),
        generator=DemoRequirementGenerator(),
    )

    project = await project_service.create_project(
        owner_uid=owner_uid,
        name="Local Requirement Demo",
        idea=idea,
    )
    result = await workflow.generate_requirements(project_id=project.id)

    return ApiResponse.ok(
        {
            "project_id": project.id,
            "run_status": result.run.status.value,
            "document_id": result.document.id if result.document else None,
            "document_version": result.document.version if result.document else None,
            "unresolved_items": result.run.output.get("unresolved_items", [])
            if result.run.output
            else [],
        }
    )


async def build_full_demo_response(
    *,
    idea: str,
    owner_uid: str,
    target_project_id: str,
) -> ApiResponse:
    """Run the local end-to-end workflow and return the API response envelope."""

    project_repository = InMemoryProjectRepository()
    project_service = ProjectService(repository=project_repository)
    document_repository = InMemoryDocumentRepository()
    document_service = DocumentService(document_repository)
    architecture_service = ArchitectureService(InMemoryArchitectureRepository())
    finding_service = SecurityFindingService(InMemorySecurityFindingRepository())
    agent_runtime = AgentRuntime(
        store=InMemoryAgentStore(),
        tool_guard=ToolGuard(DEFAULT_TOOL_DEFINITIONS),
    )

    project = await project_service.create_project(
        owner_uid=owner_uid,
        name="Local E2E Demo",
        idea=idea,
    )
    requirement_result = await RequirementWorkflowService(
        project_service=project_service,
        document_service=document_service,
        agent_runtime=agent_runtime,
        generator=DemoRequirementGenerator(),
    ).generate_requirements(project_id=project.id)
    _require_success(requirement_result.run.status, "requirement workflow")
    await project_service.transition_project(
        project_id=project.id,
        next_phase=ProjectPhase.REQUIREMENT_APPROVED,
    )
    design_result = await DesignWorkflowService(
        project_service=project_service,
        document_service=document_service,
        agent_runtime=agent_runtime,
        generator=DemoArchitectGenerator(),
    ).generate_design_document(
        project_id=project.id,
        doc_type=DocumentType.BASIC_DESIGN,
    )
    _require_success(design_result.run.status, "design workflow")
    await project_service.transition_project(
        project_id=project.id,
        next_phase=ProjectPhase.DESIGN_APPROVED,
    )
    planning_result = await PlanningWorkflowService(
        project_service=project_service,
        document_service=document_service,
        architecture_service=architecture_service,
        agent_runtime=agent_runtime,
        generator=DemoGcpPlannerGenerator(),
    ).propose_architecture(
        project_id=project.id,
        target_project_id=target_project_id,
    )
    _require_success(planning_result.run.status, "planning workflow")
    security_result = await SecurityEvaluationWorkflowService(
        project_service=project_service,
        architecture_service=architecture_service,
        finding_service=finding_service,
        agent_runtime=agent_runtime,
        evaluator=DemoSecurityEvaluator(),
    ).evaluate_latest_architecture(project_id=project.id)

    return ApiResponse.ok(
        {
            "project_id": project.id,
            "requirements_document_id": requirement_result.document.id
            if requirement_result.document
            else None,
            "basic_design_document_id": design_result.document.id if design_result.document else None,
            "architecture_id": planning_result.proposal.id if planning_result.proposal else None,
            "security_findings": len(security_result.findings),
            "security_critical_count": security_result.critical_count,
        }
    )


def _require_success(status: AgentRunStatus, operation_name: str) -> None:
    if status is not AgentRunStatus.SUCCEEDED:
        raise RuntimeError(f"{operation_name} failed: {status.value}")


def _build_requirements_doc(
    request: RequirementGenerationRequest,
    unresolved_items: list[str],
) -> str:
    unresolved_section = "\n".join(f"- {item}" for item in unresolved_items) or "- なし"
    return "\n".join(
        [
            "# 要件定義書",
            "",
            "## 1. 概要",
            request.idea,
            "",
            "## 2. 入力フォーム",
            f"- 回答数: {len(request.form_responses)}",
            "",
            "## 3. 未確定事項",
            unresolved_section,
        ]
    )
