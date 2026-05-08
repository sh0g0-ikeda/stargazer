"""Project persistence boundary."""

from __future__ import annotations

from typing import Protocol

from app.core.errors import NotFoundAppError
from app.projects.models import Project


class ProjectRepository(Protocol):
    """Storage boundary for projects."""

    async def create(self, project: Project) -> None:
        """Persist a newly-created project."""

    async def get(self, project_id: str) -> Project:
        """Return a project or raise NotFoundAppError."""

    async def update(self, project: Project) -> None:
        """Persist an existing project."""

    async def list_by_owner(self, owner_uid: str) -> list[Project]:
        """Return projects owned by one user."""


class InMemoryProjectRepository:
    """Local repository used by tests and early development."""

    def __init__(self) -> None:
        self._projects: dict[str, Project] = {}

    async def create(self, project: Project) -> None:
        self._projects[project.id] = project

    async def get(self, project_id: str) -> Project:
        try:
            return self._projects[project_id]
        except KeyError as exc:
            raise NotFoundAppError("project", project_id) from exc

    async def update(self, project: Project) -> None:
        if project.id not in self._projects:
            raise NotFoundAppError("project", project.id)
        self._projects[project.id] = project

    async def list_by_owner(self, owner_uid: str) -> list[Project]:
        return [
            project
            for project in self._projects.values()
            if project.owner_uid == owner_uid
        ]
