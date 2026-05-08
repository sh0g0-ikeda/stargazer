import unittest

from app.agents.schemas import AgentEvent
from app.agents.schemas import AgentEventType
from app.streaming.sse import encode_sse_event
from app.streaming.sse import events_since


class SseTests(unittest.TestCase):
    def test_encode_sse_event_uses_seq_as_id(self) -> None:
        event = AgentEvent.create(
            run_id="run-1",
            agent_path="/root/requirement_agent",
            seq=3,
            event_type=AgentEventType.PROGRESS,
            payload={"percent": 75, "label": "validating"},
        )

        encoded = encode_sse_event(event)

        self.assertIn("id: 3\n", encoded)
        self.assertIn("event: progress\n", encoded)
        self.assertIn('"event_type":"progress"', encoded)
        self.assertIn('"percent":75', encoded)

    def test_events_since_filters_and_sorts_by_seq(self) -> None:
        event_one = AgentEvent.create(
            run_id="run-1",
            agent_path="/root/requirement_agent",
            seq=1,
            event_type=AgentEventType.RUN_STARTED,
        )
        event_two = AgentEvent.create(
            run_id="run-1",
            agent_path="/root/requirement_agent",
            seq=2,
            event_type=AgentEventType.PROGRESS,
        )

        self.assertEqual(events_since([event_two, event_one], 1), [event_two])


if __name__ == "__main__":
    unittest.main()
