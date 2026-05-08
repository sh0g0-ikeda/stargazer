"""Application service for architecture proposals."""

from __future__ import annotations

from typing import Any

from app.architectures.models import ArchitectureEdge
from app.architectures.models import ArchitectureNode
from app.architectures.models import ArchitectureProposal
from app.architectures.models import parse_architecture_spec
from app.architectures.repository import ArchitectureRepository


class ArchitectureService:
    """Create and read architecture proposal versions."""

    def __init__(self, repository: ArchitectureRepository) -> None:
        self._repository = repository

    async def create_next_proposal(
        self,
        *,
        project_id: str,
        spec_payload: dict[str, Any],
        rationale_md: str,
        cloudbuild_yaml: str,
        gcloud_commands: tuple[str, ...],
    ) -> ArchitectureProposal:
        existing_proposals = await self._repository.list_by_project(project_id)
        spec = parse_architecture_spec(spec_payload)
        proposal = ArchitectureProposal.create(
            project_id=project_id,
            version=len(existing_proposals) + 1,
            spec=spec,
            rationale_md=rationale_md,
            cloudbuild_yaml=cloudbuild_yaml,
            gcloud_commands=gcloud_commands,
        )
        await self._repository.create(proposal)
        return proposal

    async def latest_payload(self, project_id: str) -> dict[str, Any]:
        proposal = await self._repository.latest(project_id)
        return {
            "id": proposal.id,
            "project_id": proposal.project_id,
            "version": proposal.version,
            "status": proposal.status.value,
            "spec": {
                "project_id": proposal.spec.project_id,
                "region": proposal.spec.region,
                "nodes": [_node_payload(node) for node in proposal.spec.nodes],
                "edges": [_edge_payload(edge) for edge in proposal.spec.edges],
            },
            "rationale_md": proposal.rationale_md,
            "cloudbuild_yaml": proposal.cloudbuild_yaml,
            "gcloud_commands": list(proposal.gcloud_commands),
            "created_at": proposal.created_at.isoformat(),
        }


def _node_payload(node: ArchitectureNode) -> dict[str, Any]:
    return {
        "id": node.id,
        "type": node.type.value,
        "name": node.name,
        "parameters": dict(node.parameters),
        "rationale": node.rationale,
        "cost_band": node.cost_band,
        "security_notes": list(node.security_notes),
    }


def _edge_payload(edge: ArchitectureEdge) -> dict[str, Any]:
    return {
        "id": edge.id,
        "from_node": edge.from_node,
        "to_node": edge.to_node,
        "type": edge.type.value,
        "description": edge.description,
    }
