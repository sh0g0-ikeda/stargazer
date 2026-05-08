"""Document persistence boundary."""

from __future__ import annotations

from typing import Protocol

from app.core.errors import NotFoundAppError
from app.documents.models import Document
from app.documents.models import DocumentType


class DocumentRepository(Protocol):
    """Storage boundary for immutable document versions."""

    async def create(self, document: Document) -> None:
        """Persist a document version."""

    async def latest(self, project_id: str, doc_type: DocumentType) -> Document:
        """Return the latest version for a document type."""

    async def list_versions(self, project_id: str, doc_type: DocumentType) -> list[Document]:
        """Return all versions for a document type."""


class InMemoryDocumentRepository:
    """Local document repository used by tests and early development."""

    def __init__(self) -> None:
        self._documents: dict[tuple[str, DocumentType], list[Document]] = {}

    async def create(self, document: Document) -> None:
        key = (document.project_id, document.doc_type)
        versions = self._documents.setdefault(key, [])
        if any(existing.version == document.version for existing in versions):
            raise ValueError(
                f"document version already exists: {document.doc_type.value} v{document.version}"
            )
        versions.append(document)
        versions.sort(key=lambda item: item.version)

    async def latest(self, project_id: str, doc_type: DocumentType) -> Document:
        versions = await self.list_versions(project_id, doc_type)
        if not versions:
            raise NotFoundAppError("document", f"{project_id}:{doc_type.value}")
        return versions[-1]

    async def list_versions(self, project_id: str, doc_type: DocumentType) -> list[Document]:
        return list(self._documents.get((project_id, doc_type), []))
