"""Code generation persistence boundary."""

from __future__ import annotations

from typing import Protocol

from app.codegen.models import CodeGenerationResult
from app.core.errors import NotFoundAppError


class CodeGenerationRepository(Protocol):
    """Storage boundary for generated code packages."""

    async def create(self, result: CodeGenerationResult) -> None:
        """Persist generated code."""

    async def latest(self, project_id: str) -> CodeGenerationResult:
        """Return the latest generated package for one project."""


class InMemoryCodeGenerationRepository:
    """Local code generation repository used by tests and demo mode."""

    def __init__(self) -> None:
        self._results: dict[str, list[CodeGenerationResult]] = {}

    async def create(self, result: CodeGenerationResult) -> None:
        self._results.setdefault(result.project_id, []).append(result)

    async def latest(self, project_id: str) -> CodeGenerationResult:
        results = self._results.get(project_id, [])
        if not results:
            raise NotFoundAppError("code_generation", project_id)
        return results[-1]
