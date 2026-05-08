"""Cloud Build adapter boundary and local demo implementation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from typing import Protocol
from uuid import uuid4

from app.deployments.models import BuildStatus
from app.deployments.pipeline import render_cloud_run_apply_plan


@dataclass(frozen=True)
class BuildResult:
    """Result from one build/apply execution."""

    build_id: str
    status: BuildStatus
    deployed_url: str | None
    logs: tuple[str, ...]


class CloudBuildAdapter(Protocol):
    """Boundary for starting and observing Cloud Build."""

    async def trigger_apply(self, *, architecture_payload: dict[str, Any]) -> BuildResult:
        """Apply an architecture proposal."""


class LocalCloudBuildAdapter:
    """Deterministic local adapter used until real GCP credentials are configured."""

    async def trigger_apply(self, *, architecture_payload: dict[str, Any]) -> BuildResult:
        plan = render_cloud_run_apply_plan(architecture_payload=architecture_payload)
        return BuildResult(
            build_id=f"local-build-{uuid4()}",
            status=BuildStatus.SUCCEEDED,
            deployed_url=plan.deployed_url,
            logs=(
                f"rendered cloudbuild.yaml for {plan.service_name}",
                f"image: {plan.image_uri}",
                f"validated {len(plan.gcloud_commands)} gcloud command(s)",
                "simulated Cloud Build success",
                f"published url: {plan.deployed_url}",
            ),
        )
