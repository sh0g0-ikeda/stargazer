import unittest

from app.core.errors import NotFoundAppError
from app.core.errors import ValidationAppError
from app.documents.models import DocumentType
from app.documents.repository import InMemoryDocumentRepository
from app.documents.service import DocumentService


class DocumentServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_create_next_version_increments_versions(self) -> None:
        service = DocumentService(InMemoryDocumentRepository())

        first = await service.create_next_version(
            project_id="project-1",
            doc_type=DocumentType.REQUIREMENTS,
            content_md="# 要件定義書\n\nv1",
            generated_by="requirement_agent",
            prompt_text="prompt v1",
        )
        second = await service.create_next_version(
            project_id="project-1",
            doc_type=DocumentType.REQUIREMENTS,
            content_md="# 要件定義書\n\nv2",
            generated_by="requirement_agent",
            prompt_text="prompt v2",
        )

        self.assertEqual(first.version, 1)
        self.assertEqual(second.version, 2)

    async def test_latest_payload_returns_api_safe_shape(self) -> None:
        service = DocumentService(InMemoryDocumentRepository())
        document = await service.create_next_version(
            project_id="project-1",
            doc_type=DocumentType.REQUIREMENTS,
            content_md="# 要件定義書",
            generated_by="requirement_agent",
            prompt_text="prompt",
            references=(" project:project-1 ",),
        )

        payload = await service.latest_payload("project-1", DocumentType.REQUIREMENTS)

        self.assertEqual(payload["id"], document.id)
        self.assertEqual(payload["doc_type"], "requirements")
        self.assertEqual(payload["references"], ["project:project-1"])

    async def test_latest_missing_document_raises_not_found(self) -> None:
        service = DocumentService(InMemoryDocumentRepository())

        with self.assertRaises(NotFoundAppError):
            await service.latest_payload("project-1", DocumentType.REQUIREMENTS)

    async def test_empty_document_content_is_rejected(self) -> None:
        service = DocumentService(InMemoryDocumentRepository())

        with self.assertRaises(ValidationAppError):
            await service.create_next_version(
                project_id="project-1",
                doc_type=DocumentType.REQUIREMENTS,
                content_md=" ",
                generated_by="requirement_agent",
                prompt_text="prompt",
            )

    async def test_empty_prompt_text_is_rejected(self) -> None:
        service = DocumentService(InMemoryDocumentRepository())

        with self.assertRaises(ValidationAppError):
            await service.create_next_version(
                project_id="project-1",
                doc_type=DocumentType.REQUIREMENTS,
                content_md="# 要件定義書",
                generated_by="requirement_agent",
                prompt_text=" ",
            )


if __name__ == "__main__":
    unittest.main()
