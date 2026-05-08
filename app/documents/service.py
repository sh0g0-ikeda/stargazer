"""Application service for versioned documents."""

from __future__ import annotations

from dataclasses import asdict
from hashlib import sha256
from typing import Any

from app.core.errors import ValidationAppError
from app.documents.models import Document
from app.documents.models import DocumentType
from app.documents.repository import DocumentRepository


class DocumentService:
    """Create and read immutable document versions."""

    def __init__(self, repository: DocumentRepository) -> None:
        self._repository = repository

    async def create_next_version(
        self,
        *,
        project_id: str,
        doc_type: DocumentType,
        content_md: str,
        generated_by: str,
        prompt_text: str,
        references: tuple[str, ...] = (),
    ) -> Document:
        existing_versions = await self._repository.list_versions(project_id, doc_type)
        next_version = len(existing_versions) + 1
        document = Document.create(
            project_id=project_id,
            doc_type=doc_type,
            version=next_version,
            content_md=content_md,
            generated_by=generated_by,
            prompt_hash=_hash_prompt(prompt_text),
            references=references,
        )
        await self._repository.create(document)
        return document

    async def latest_payload(self, project_id: str, doc_type: DocumentType) -> dict[str, Any]:
        document = await self._repository.latest(project_id, doc_type)
        payload = asdict(document)
        payload["doc_type"] = document.doc_type.value
        payload["created_at"] = document.created_at.isoformat()
        payload["references"] = list(document.references)
        return payload

    async def latest_document(self, project_id: str, doc_type: DocumentType) -> Document:
        """Return the latest immutable document version."""

        return await self._repository.latest(project_id, doc_type)


def _hash_prompt(prompt_text: str) -> str:
    if not prompt_text.strip():
        raise ValidationAppError("prompt_text must not be empty")
    return sha256(prompt_text.encode("utf-8")).hexdigest()
