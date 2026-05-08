import unittest

from app.agents.roles import REQUIREMENT_AGENT
from app.agents.schemas import AgentRun
from app.agents.schemas import AgentRunStatus
from app.agents.schemas import utc_now
from app.core.errors import ValidationAppError
from app.timeline.models import TimelineCategory
from app.timeline.models import TimelineEvent
from app.timeline.models import TimelineResult
from app.timeline.repository import InMemoryTimelineRepository
from app.timeline.service import TimelineService


class TimelineServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_record_agent_run_creates_user_facing_event(self) -> None:
        service = TimelineService(InMemoryTimelineRepository())
        run = AgentRun.create(
            project_id="project-1",
            role=REQUIREMENT_AGENT,
            agent_path="/root/requirement_agent",
            input_snapshot={"idea": "app"},
        )
        run.status = AgentRunStatus.SUCCEEDED
        run.progress_percent = 100
        run.started_at = utc_now()
        run.finished_at = utc_now()

        event = await service.record_agent_run(
            run=run,
            action="generated_requirements",
            target={"type": "document", "id": "doc-1"},
        )
        payloads = await service.list_payloads("project-1")

        self.assertEqual(event.result, TimelineResult.SUCCESS)
        self.assertEqual(payloads[0]["category"], "agent_action")
        self.assertEqual(payloads[0]["metadata"]["run_id"], run.id)

    async def test_timeline_event_rejects_invalid_target(self) -> None:
        with self.assertRaises(ValidationAppError):
            TimelineEvent.create(
                project_id="project-1",
                category=TimelineCategory.AGENT_ACTION,
                action="generated_requirements",
                result=TimelineResult.SUCCESS,
                target={"type": "document"},
            )


if __name__ == "__main__":
    unittest.main()
