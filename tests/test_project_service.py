import unittest

from app.core.errors import PhaseConflictAppError
from app.core.errors import ValidationAppError
from app.projects.models import ProjectPhase
from app.projects.repository import InMemoryProjectRepository
from app.projects.service import ProjectService


class ProjectServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_create_project_validates_and_persists_project(self) -> None:
        service = ProjectService(repository=InMemoryProjectRepository())

        project = await service.create_project(
            owner_uid="user-1",
            name="Support Desk",
            idea="問い合わせ管理アプリ",
        )

        self.assertEqual(project.owner_uid, "user-1")
        self.assertEqual(project.phase, ProjectPhase.DRAFT)

    async def test_create_project_rejects_empty_idea(self) -> None:
        service = ProjectService(repository=InMemoryProjectRepository())

        with self.assertRaises(ValidationAppError):
            await service.create_project(owner_uid="user-1", name="App", idea=" ")

    async def test_transition_project_allows_defined_next_phase(self) -> None:
        service = ProjectService(repository=InMemoryProjectRepository())
        project = await service.create_project(
            owner_uid="user-1",
            name="Support Desk",
            idea="問い合わせ管理アプリ",
        )

        updated = await service.transition_project(
            project_id=project.id,
            next_phase=ProjectPhase.REQUIREMENT_DRAFT,
        )

        self.assertEqual(updated.phase, ProjectPhase.REQUIREMENT_DRAFT)

    async def test_transition_project_rejects_invalid_phase_jump(self) -> None:
        service = ProjectService(repository=InMemoryProjectRepository())
        project = await service.create_project(
            owner_uid="user-1",
            name="Support Desk",
            idea="問い合わせ管理アプリ",
        )

        with self.assertRaises(PhaseConflictAppError):
            await service.transition_project(
                project_id=project.id,
                next_phase=ProjectPhase.DEPLOYED,
            )


if __name__ == "__main__":
    unittest.main()
