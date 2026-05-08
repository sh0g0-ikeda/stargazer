"""Requirement agent implementation."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any
from typing import Protocol

from app.agents.runtime import AgentExecutionContext
from app.core.errors import ValidationAppError


class RequirementGenerator(Protocol):
    """Boundary for LLM-backed requirement generation."""

    async def generate(self, request: "RequirementGenerationRequest") -> dict[str, Any]:
        """Return untrusted generated requirement output."""


@dataclass(frozen=True)
class RequirementGenerationRequest:
    """Validated input passed to the requirement generator."""

    idea: str
    form_responses: Mapping[str, Any]
    follow_up_answers: Mapping[str, str]


@dataclass(frozen=True)
class RequirementOutput:
    """Validated output returned by RequirementAgent."""

    requirements_doc_md: str
    unresolved_items: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "requirements_doc_md": self.requirements_doc_md,
            "unresolved_items": list(self.unresolved_items),
        }


@dataclass(frozen=True)
class FollowUpQuestionOutput:
    """Validated follow-up question output returned by RequirementAgent."""

    follow_up_questions: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {"follow_up_questions": list(self.follow_up_questions)}


class RequirementAgent:
    """Generate a requirements document from project intake data."""

    def __init__(self, generator: RequirementGenerator) -> None:
        self._generator = generator

    async def run(self, context: AgentExecutionContext) -> dict[str, Any]:
        await context.progress(15, "validating requirement input")
        request = _parse_generation_request(context.input_snapshot)

        read_decision = await context.request_tool(
            "read_project",
            {"project_id": context.run.project_id},
        )
        if not read_decision.allowed:
            raise PermissionError(read_decision.message)

        await context.progress(25, "generating requirements")
        generated_output = await self._generator.generate(request)
        if not isinstance(generated_output, Mapping):
            raise ValidationAppError("requirement generator output must be an object")

        await context.progress(75, "validating generated requirements")
        requirement_output = _parse_requirement_output(generated_output)

        write_decision = await context.request_tool(
            "write_document",
            {
                "project_id": context.run.project_id,
                "doc_type": "requirements",
            },
        )
        if not write_decision.allowed:
            raise PermissionError(write_decision.message)

        await context.progress(90, "requirements ready")
        return requirement_output.to_dict()


class RequirementQuestionAgent:
    """Generate up to three follow-up questions from project intake data."""

    def __init__(self, generator: RequirementGenerator) -> None:
        self._generator = generator

    async def run(self, context: AgentExecutionContext) -> dict[str, Any]:
        await context.progress(15, "validating follow-up input")
        request = _parse_generation_request(context.input_snapshot)

        read_decision = await context.request_tool(
            "read_project",
            {"project_id": context.run.project_id},
        )
        if not read_decision.allowed:
            raise PermissionError(read_decision.message)

        await context.progress(35, "generating follow-up questions")
        generated_output = await self._generator.generate(request)
        if not isinstance(generated_output, Mapping):
            raise ValidationAppError("requirement generator output must be an object")

        await context.progress(80, "validating follow-up questions")
        follow_up_output = _parse_follow_up_question_output(generated_output)
        await context.progress(90, "follow-up questions ready")
        return follow_up_output.to_dict()


def _parse_generation_request(payload: Mapping[str, Any]) -> RequirementGenerationRequest:
    idea = payload.get("idea")
    if not isinstance(idea, str) or not idea.strip():
        raise ValidationAppError("idea must be a non-empty string")

    form_responses = payload.get("form_responses", {})
    if not isinstance(form_responses, Mapping):
        raise ValidationAppError("form_responses must be an object")
    for form_key in form_responses:
        if not isinstance(form_key, str):
            raise ValidationAppError("form_responses keys must be strings")

    follow_up_answers = payload.get("follow_up_answers", {})
    if not isinstance(follow_up_answers, Mapping):
        raise ValidationAppError("follow_up_answers must be an object")

    normalized_answers: dict[str, str] = {}
    for question_id, answer in follow_up_answers.items():
        if not isinstance(question_id, str) or not isinstance(answer, str):
            raise ValidationAppError("follow_up_answers must map strings to strings")
        normalized_answers[question_id] = answer

    return RequirementGenerationRequest(
        idea=idea.strip(),
        form_responses=dict(form_responses),
        follow_up_answers=normalized_answers,
    )


def _parse_requirement_output(payload: Mapping[str, Any]) -> RequirementOutput:
    requirements_doc_md = payload.get("requirements_doc_md")
    if not isinstance(requirements_doc_md, str) or not requirements_doc_md.strip():
        raise ValidationAppError("requirements_doc_md must be a non-empty string")

    unresolved_items = payload.get("unresolved_items", [])
    if not isinstance(unresolved_items, list):
        raise ValidationAppError("unresolved_items must be a list")

    normalized_unresolved_items: list[str] = []
    for item in unresolved_items:
        if not isinstance(item, str):
            raise ValidationAppError("unresolved_items must contain only strings")
        if item.strip():
            normalized_unresolved_items.append(item.strip())

    return RequirementOutput(
        requirements_doc_md=requirements_doc_md.strip(),
        unresolved_items=normalized_unresolved_items,
    )


def _parse_follow_up_question_output(payload: Mapping[str, Any]) -> FollowUpQuestionOutput:
    follow_up_questions = payload.get("follow_up_questions", [])
    if not isinstance(follow_up_questions, list):
        raise ValidationAppError("follow_up_questions must be a list")
    if len(follow_up_questions) > 3:
        raise ValidationAppError("follow_up_questions must contain at most 3 questions")

    normalized_questions: list[str] = []
    for question in follow_up_questions:
        if not isinstance(question, str):
            raise ValidationAppError("follow_up_questions must contain only strings")
        if question.strip():
            normalized_questions.append(question.strip())

    return FollowUpQuestionOutput(follow_up_questions=normalized_questions)
