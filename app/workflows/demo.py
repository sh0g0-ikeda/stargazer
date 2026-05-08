"""Local demo helpers for exercising workflows without cloud dependencies."""

from __future__ import annotations

from typing import Any

from app.agents.requirement import RequirementGenerationRequest
from app.agents.runtime import AgentRuntime
from app.agents.runtime import InMemoryAgentStore
from app.agents.tool_guard import DEFAULT_TOOL_DEFINITIONS
from app.agents.tool_guard import ToolGuard
from app.api.responses import ApiResponse
from app.documents.repository import InMemoryDocumentRepository
from app.documents.service import DocumentService
from app.projects.repository import InMemoryProjectRepository
from app.projects.service import ProjectService
from app.workflows.requirements import RequirementWorkflowService


class DemoRequirementGenerator:
    """Deterministic requirement generator used for local smoke tests."""

    async def generate(self, request: RequirementGenerationRequest) -> dict[str, Any]:
        unresolved_items = []
        if "auth" not in request.follow_up_answers:
            unresolved_items.append("認証方式")

        return {
            "requirements_doc_md": _build_requirements_doc(request, unresolved_items),
            "unresolved_items": unresolved_items,
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
