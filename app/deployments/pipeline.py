"""Cloud Build apply plan rendering.

The renderer keeps deployment command generation deterministic and separate
from the adapter that starts Cloud Build. This makes the dangerous part of the
pipeline visible and testable before a real GCP adapter is wired in.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import re
from typing import Any

from app.core.errors import ValidationAppError


_GCP_PROJECT_ID_RE = re.compile(r"^[a-z][a-z0-9-]{4,28}[a-z0-9]$")
_REGION_RE = re.compile(r"^[a-z]+-[a-z]+[0-9]$")
_SERVICE_NAME_RE = re.compile(r"^[a-z][a-z0-9-]{0,62}$")


@dataclass(frozen=True)
class CloudBuildApplyPlan:
    """Commands and metadata needed to apply one Cloud Run target service."""

    project_id: str
    region: str
    service_name: str
    image_uri: str
    deployed_url: str
    cloudbuild_yaml: str
    gcloud_commands: tuple[str, ...]


def render_cloud_run_apply_plan(*, architecture_payload: dict[str, Any]) -> CloudBuildApplyPlan:
    """Render a Cloud Build plan from a validated architecture payload."""

    spec = architecture_payload.get("spec")
    if not isinstance(spec, dict):
        raise ValidationAppError("architecture payload must include spec")
    project_id = _validate_project_id(_required_string(spec, "project_id"))
    region = _validate_region(_required_string(spec, "region"))
    cloud_run_node = _find_cloud_run_node(spec)
    service_name = _service_name_from_node(cloud_run_node)
    parameters = _node_parameters(cloud_run_node)
    image_uri = f"{region}-docker.pkg.dev/{project_id}/castorops/{service_name}:latest"
    deployed_url = f"https://{service_name}-{project_id}.run.app"
    deploy_command = _deploy_command(
        project_id=project_id,
        region=region,
        service_name=service_name,
        image_uri=image_uri,
        parameters=parameters,
    )
    gcloud_commands = (
        f"gcloud config set project {project_id}",
        "gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com",
        f"gcloud artifacts repositories create castorops --repository-format=docker --location={region} --quiet",
        deploy_command,
    )
    return CloudBuildApplyPlan(
        project_id=project_id,
        region=region,
        service_name=service_name,
        image_uri=image_uri,
        deployed_url=deployed_url,
        cloudbuild_yaml=_cloudbuild_yaml(
            image_uri=image_uri,
            deploy_command=deploy_command,
        ),
        gcloud_commands=gcloud_commands,
    )


def _cloudbuild_yaml(*, image_uri: str, deploy_command: str) -> str:
    quoted_image_uri = json.dumps(image_uri)
    quoted_deploy_command = json.dumps(deploy_command)
    return "\n".join(
        [
            "steps:",
            "  - name: gcr.io/cloud-builders/docker",
            "    args:",
            "      - build",
            "      - -t",
            f"      - {quoted_image_uri}",
            "      - .",
            "  - name: gcr.io/cloud-builders/docker",
            "    args:",
            "      - push",
            f"      - {quoted_image_uri}",
            "  - name: gcr.io/google.com/cloudsdktool/cloud-sdk",
            "    entrypoint: bash",
            "    args:",
            "      - -lc",
            f"      - {quoted_deploy_command}",
            "images:",
            f"  - {quoted_image_uri}",
        ]
    )


def _deploy_command(
    *,
    project_id: str,
    region: str,
    service_name: str,
    image_uri: str,
    parameters: dict[str, Any],
) -> str:
    command_parts = [
        "gcloud run deploy",
        service_name,
        f"--image={image_uri}",
        f"--project={project_id}",
        f"--region={region}",
        "--platform=managed",
        f"--memory={_memory(parameters)}",
        f"--cpu={_cpu(parameters)}",
        f"--min-instances={_non_negative_int(parameters, 'min_instances', 0)}",
        f"--max-instances={_non_negative_int(parameters, 'max_instances', 10)}",
        "--quiet",
    ]
    if parameters.get("allow_unauthenticated") is True:
        command_parts.append("--allow-unauthenticated")
    else:
        command_parts.append("--no-allow-unauthenticated")
    return " ".join(command_parts)


def _find_cloud_run_node(spec: dict[str, Any]) -> dict[str, Any]:
    nodes = spec.get("nodes")
    if not isinstance(nodes, list):
        raise ValidationAppError("architecture spec nodes must be a list")
    for node in nodes:
        if isinstance(node, dict) and node.get("type") == "cloud_run":
            return node
    raise ValidationAppError("architecture spec must include a cloud_run node")


def _service_name_from_node(node: dict[str, Any]) -> str:
    raw_name = str(node.get("id") or node.get("name") or "target")
    normalized = raw_name.strip().lower().replace("_", "-")
    normalized = re.sub(r"[^a-z0-9-]+", "-", normalized)
    normalized = re.sub(r"-+", "-", normalized).strip("-")
    if not normalized or not normalized[0].isalpha():
        normalized = f"svc-{normalized}"
    normalized = normalized[:63].rstrip("-")
    if not _SERVICE_NAME_RE.match(normalized):
        raise ValidationAppError("cloud run service name is invalid", {"service_name": normalized})
    return normalized


def _node_parameters(node: dict[str, Any]) -> dict[str, Any]:
    parameters = node.get("parameters", {})
    if not isinstance(parameters, dict):
        raise ValidationAppError("cloud_run node parameters must be an object")
    return parameters


def _memory(parameters: dict[str, Any]) -> str:
    value = parameters.get("memory", "512Mi")
    if not isinstance(value, str) or not value.strip():
        raise ValidationAppError("cloud_run memory must be a non-empty string")
    return value.strip()


def _cpu(parameters: dict[str, Any]) -> str:
    value = parameters.get("cpu", "1")
    if not isinstance(value, str) or not value.strip():
        raise ValidationAppError("cloud_run cpu must be a non-empty string")
    return value.strip()


def _non_negative_int(parameters: dict[str, Any], field_name: str, default: int) -> int:
    value = parameters.get(field_name, default)
    if not isinstance(value, int) or value < 0:
        raise ValidationAppError(f"cloud_run {field_name} must be a non-negative integer")
    return value


def _validate_project_id(project_id: str) -> str:
    if not _GCP_PROJECT_ID_RE.match(project_id):
        raise ValidationAppError("target GCP project id is invalid", {"project_id": project_id})
    return project_id


def _validate_region(region: str) -> str:
    if not _REGION_RE.match(region):
        raise ValidationAppError("target GCP region is invalid", {"region": region})
    return region


def _required_string(payload: dict[str, Any], field_name: str) -> str:
    value = payload.get(field_name)
    if not isinstance(value, str) or not value.strip():
        raise ValidationAppError(f"{field_name} must be a non-empty string")
    return value.strip()
