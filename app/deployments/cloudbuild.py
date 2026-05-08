"""Cloud Build adapter boundary and local demo implementation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from typing import Protocol
from uuid import uuid4

from app.deployments.models import BuildStatus


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
        spec = architecture_payload["spec"]
        target_project_id = spec["project_id"]
        service_name = _service_name(spec)
        deployed_url = f"https://{service_name}-{target_project_id}.run.app"
        return BuildResult(
            build_id=f"local-build-{uuid4()}",
            status=BuildStatus.SUCCEEDED,
            deployed_url=deployed_url,
            logs=(
                "rendered cloudbuild.yaml",
                "validated gcloud command sequence",
                "simulated Cloud Build success",
                f"published url: {deployed_url}",
            ),
        )


def _service_name(spec: dict[str, Any]) -> str:
    for node in spec.get("nodes", []):
        if node.get("type") == "cloud_run":
            return str(node.get("id", "target")).replace("_", "-")
    return "target"
