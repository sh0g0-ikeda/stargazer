"""Run the local end-to-end CastorOps workflow demo."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.bootstrap import build_demo_facade
from app.api.responses import ApiResponse


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run CastorOps local E2E workflow demo.")
    parser.add_argument("--idea", required=True, help="Project idea text.")
    parser.add_argument("--owner-uid", default="local-user", help="Owner user id.")
    parser.add_argument("--target-project-id", default="demo-gcp-project", help="Target GCP project id.")
    return parser.parse_args()


async def run() -> None:
    args = parse_args()
    response = await build_full_mvp_demo_response(
        idea=args.idea,
        target_project_id=args.target_project_id,
    )
    print(json.dumps(response.to_dict(), ensure_ascii=False, indent=2))


async def build_full_mvp_demo_response(
    *,
    idea: str,
    target_project_id: str,
) -> ApiResponse:
    facade = build_demo_facade()
    create_response = await facade.create_project(
        name="Local E2E Demo",
        idea=idea,
    )
    project_id = create_response.to_dict()["data"]["id"]

    follow_up_response = await facade.generate_follow_up_questions(project_id=project_id)
    requirements_response = await facade.generate_requirements(project_id=project_id)
    await facade.decide_approval(
        project_id=project_id,
        gate="requirements",
        decision="approved",
        snapshot=requirements_response.to_dict()["data"],
    )
    design_response = await facade.generate_design_set(project_id=project_id)
    await facade.decide_approval(
        project_id=project_id,
        gate="design",
        decision="approved",
        snapshot={"documents": design_response.to_dict()["data"]},
    )
    architecture_response = await facade.propose_architecture(
        project_id=project_id,
        target_project_id=target_project_id,
    )
    security_response = await facade.evaluate_security(project_id=project_id)
    await facade.decide_approval(
        project_id=project_id,
        gate="architecture",
        decision="approved",
        snapshot={
            "architecture": architecture_response.to_dict()["data"],
            "security": security_response.to_dict()["data"],
        },
    )
    target_app_response = await facade.generate_target_app(
        project_id=project_id,
        app_name="Support Desk API",
        collection_name="support_tickets",
        fields=("subject", "message", "email"),
    )
    apply_response = await facade.apply_latest_architecture(project_id=project_id)
    ops_response = await facade.ops_overview(project_id=project_id)
    timeline_response = await facade.timeline(project_id=project_id)

    return ApiResponse.ok(
        {
            "project_id": project_id,
            "follow_up_questions": follow_up_response.to_dict()["data"]["follow_up_questions"],
            "requirements": requirements_response.to_dict()["data"],
            "design_documents": design_response.to_dict()["data"],
            "architecture": architecture_response.to_dict()["data"],
            "security": security_response.to_dict()["data"],
            "target_app": target_app_response.to_dict()["data"],
            "deployment": apply_response.to_dict()["data"],
            "ops_sections": list(ops_response.to_dict()["data"].keys()),
            "timeline_events": len(timeline_response.to_dict()["data"]),
        }
    )


if __name__ == "__main__":
    asyncio.run(run())
