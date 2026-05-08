"""Architecture proposal models."""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from app.agents.schemas import utc_now
from app.core.errors import ValidationAppError


class ArchitectureStatus(str, Enum):
    """Lifecycle status for architecture proposals."""

    PROPOSED = "proposed"
    APPROVED = "approved"
    APPLIED = "applied"
    ERROR = "error"


class ArchitectureNodeType(str, Enum):
    """Supported MVP architecture node types."""

    CLOUD_RUN = "cloud_run"
    FIRESTORE = "firestore"
    SECRET_MANAGER = "secret_manager"
    CLOUD_STORAGE = "cloud_storage"
    CLOUD_LOGGING = "cloud_logging"
    CLOUD_MONITORING = "cloud_monitoring"
    ARTIFACT_REGISTRY = "artifact_registry"
    IAM_SERVICE_ACCOUNT = "iam_sa"
    EXTERNAL = "external"


class ArchitectureEdgeType(str, Enum):
    """Supported MVP architecture edge types."""

    HTTP = "http"
    DB_RW = "db_rw"
    SECRET_READ = "secret_read"
    LOG_OUTPUT = "log_output"
    IMAGE_PULL = "image_pull"
    IAM_BINDING = "iam_binding"


@dataclass(frozen=True)
class ArchitectureNode:
    """One node in an architecture proposal."""

    id: str
    type: ArchitectureNodeType
    name: str
    parameters: dict[str, Any]
    rationale: str
    cost_band: str
    security_notes: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class ArchitectureEdge:
    """One directed relationship between architecture nodes."""

    id: str
    from_node: str
    to_node: str
    type: ArchitectureEdgeType
    description: str


@dataclass(frozen=True)
class ArchitectureSpec:
    """Validated GCP architecture proposal."""

    project_id: str
    region: str
    nodes: tuple[ArchitectureNode, ...]
    edges: tuple[ArchitectureEdge, ...]


@dataclass(frozen=True)
class ArchitectureProposal:
    """Persisted architecture proposal version."""

    id: str
    project_id: str
    version: int
    status: ArchitectureStatus
    spec: ArchitectureSpec
    rationale_md: str
    cloudbuild_yaml: str
    gcloud_commands: tuple[str, ...]
    created_at: datetime = field(default_factory=utc_now)

    @classmethod
    def create(
        cls,
        *,
        project_id: str,
        version: int,
        spec: ArchitectureSpec,
        rationale_md: str,
        cloudbuild_yaml: str,
        gcloud_commands: tuple[str, ...],
    ) -> "ArchitectureProposal":
        if version <= 0:
            raise ValidationAppError("architecture version must be positive")
        if not rationale_md.strip():
            raise ValidationAppError("rationale_md must not be empty")
        if not cloudbuild_yaml.strip():
            raise ValidationAppError("cloudbuild_yaml must not be empty")
        if not gcloud_commands:
            raise ValidationAppError("gcloud_commands must not be empty")
        for command in gcloud_commands:
            if not command.strip():
                raise ValidationAppError("gcloud_commands must not contain empty commands")

        return cls(
            id=str(uuid4()),
            project_id=project_id,
            version=version,
            status=ArchitectureStatus.PROPOSED,
            spec=spec,
            rationale_md=rationale_md.strip(),
            cloudbuild_yaml=cloudbuild_yaml.strip(),
            gcloud_commands=tuple(command.strip() for command in gcloud_commands),
        )


def parse_architecture_spec(payload: dict[str, Any]) -> ArchitectureSpec:
    """Parse and validate an untrusted ArchitectureSpec payload."""

    project_id = _required_string(payload, "project_id")
    region = _required_string(payload, "region")
    raw_nodes = payload.get("nodes")
    raw_edges = payload.get("edges", [])
    if not isinstance(raw_nodes, list) or not raw_nodes:
        raise ValidationAppError("architecture spec must include at least one node")
    if not isinstance(raw_edges, list):
        raise ValidationAppError("architecture spec edges must be a list")

    nodes = tuple(_parse_node(node) for node in raw_nodes)
    node_ids = [node.id for node in nodes]
    if len(set(node_ids)) != len(node_ids):
        raise ValidationAppError("architecture node ids must be unique")

    edges = tuple(_parse_edge(edge) for edge in raw_edges)
    node_id_set = set(node_ids)
    for edge in edges:
        if edge.from_node not in node_id_set or edge.to_node not in node_id_set:
            raise ValidationAppError(
                "architecture edges must reference existing nodes",
                {"edge_id": edge.id},
            )

    return ArchitectureSpec(project_id=project_id, region=region, nodes=nodes, edges=edges)


def _parse_node(payload: Any) -> ArchitectureNode:
    if not isinstance(payload, dict):
        raise ValidationAppError("architecture node must be an object")
    raw_type = _required_string(payload, "type")
    try:
        node_type = ArchitectureNodeType(raw_type)
    except ValueError as exc:
        raise ValidationAppError("architecture node type is not supported", {"type": raw_type}) from exc
    parameters = payload.get("parameters", {})
    if not isinstance(parameters, dict):
        raise ValidationAppError("architecture node parameters must be an object")
    security_notes = payload.get("security_notes", [])
    if not isinstance(security_notes, list) or not all(isinstance(item, str) for item in security_notes):
        raise ValidationAppError("architecture node security_notes must be a string list")
    return ArchitectureNode(
        id=_required_string(payload, "id"),
        type=node_type,
        name=_required_string(payload, "name"),
        parameters=dict(parameters),
        rationale=_required_string(payload, "rationale"),
        cost_band=_required_string(payload, "cost_band"),
        security_notes=tuple(item.strip() for item in security_notes if item.strip()),
    )


def _parse_edge(payload: Any) -> ArchitectureEdge:
    if not isinstance(payload, dict):
        raise ValidationAppError("architecture edge must be an object")
    raw_type = _required_string(payload, "type")
    try:
        edge_type = ArchitectureEdgeType(raw_type)
    except ValueError as exc:
        raise ValidationAppError("architecture edge type is not supported", {"type": raw_type}) from exc
    return ArchitectureEdge(
        id=_required_string(payload, "id"),
        from_node=_required_string(payload, "from_node"),
        to_node=_required_string(payload, "to_node"),
        type=edge_type,
        description=_required_string(payload, "description"),
    )


def _required_string(payload: dict[str, Any], field_name: str) -> str:
    value = payload.get(field_name)
    if not isinstance(value, str) or not value.strip():
        raise ValidationAppError(f"{field_name} must be a non-empty string")
    return value.strip()
