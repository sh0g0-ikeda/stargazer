"""Architect agent implementation."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any
from typing import Protocol

from app.agents.runtime import AgentExecutionContext
from app.core.errors import ValidationAppError
from app.documents.models import DocumentType


ARCHITECT_DOCUMENT_TYPES = frozenset(
    {
        DocumentType.BASIC_DESIGN,
        DocumentType.API_DESIGN,
        DocumentType.DATA_DESIGN,
        DocumentType.OPS_DESIGN,
        DocumentType.SECURITY_DESIGN,
        DocumentType.ADR,
        DocumentType.TASKS,
    }
)


class ArchitectGenerator(Protocol):
    """Boundary for LLM-backed design document generation."""

    async def generate(self, request: "ArchitectGenerationRequest") -> dict[str, Any]:
        """Return untrusted generated design output."""


@dataclass(frozen=True)
class ArchitectGenerationRequest:
    """Validated input passed to the architect generator."""

    requirements_doc_md: str
    doc_type: DocumentType


@dataclass(frozen=True)
class ArchitectOutput:
    """Validated Architect Agent output."""

    doc_md: str
    references: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "doc_md": self.doc_md,
            "references": list(self.references),
        }


class ArchitectAgent:
    """Generate one design document from an approved requirements document."""

    def __init__(self, generator: ArchitectGenerator) -> None:
        self._generator = generator

    async def run(self, context: AgentExecutionContext) -> dict[str, Any]:
        await context.progress(15, "validating architect input")
        request = _parse_generation_request(context.input_snapshot)

        read_decision = await context.request_tool(
            "read_document",
            {"doc_type": DocumentType.REQUIREMENTS.value},
        )
        if not read_decision.allowed:
            raise PermissionError(read_decision.message)

        await context.progress(25, "generating design document")
        generated_output = await self._generator.generate(request)
        if not isinstance(generated_output, Mapping):
            raise ValidationAppError("architect generator output must be an object")

        await context.progress(75, "validating design document")
        architect_output = _parse_architect_output(generated_output)

        write_decision = await context.request_tool(
            "write_document",
            {"doc_type": request.doc_type.value},
        )
        if not write_decision.allowed:
            raise PermissionError(write_decision.message)

        await context.progress(90, "design document ready")
        return architect_output.to_dict()


def _parse_generation_request(payload: Mapping[str, Any]) -> ArchitectGenerationRequest:
    requirements_doc_md = payload.get("requirements_doc_md")
    if not isinstance(requirements_doc_md, str) or not requirements_doc_md.strip():
        raise ValidationAppError("requirements_doc_md must be a non-empty string")

    raw_doc_type = payload.get("doc_type")
    if not isinstance(raw_doc_type, str):
        raise ValidationAppError("doc_type must be a string")
    try:
        doc_type = DocumentType(raw_doc_type)
    except ValueError as exc:
        raise ValidationAppError("doc_type is not supported", {"doc_type": raw_doc_type}) from exc

    if doc_type not in ARCHITECT_DOCUMENT_TYPES:
        raise ValidationAppError("doc_type is not an architect document", {"doc_type": raw_doc_type})

    return ArchitectGenerationRequest(
        requirements_doc_md=requirements_doc_md.strip(),
        doc_type=doc_type,
    )


def _parse_architect_output(payload: Mapping[str, Any]) -> ArchitectOutput:
    doc_md = payload.get("doc_md")
    if not isinstance(doc_md, str) or not doc_md.strip():
        raise ValidationAppError("doc_md must be a non-empty string")

    references = payload.get("references", [])
    if not isinstance(references, list):
        raise ValidationAppError("references must be a list")

    normalized_references: list[str] = []
    for reference in references:
        if not isinstance(reference, str):
            raise ValidationAppError("references must contain only strings")
        if reference.strip():
            normalized_references.append(reference.strip())

    return ArchitectOutput(doc_md=doc_md.strip(), references=normalized_references)
