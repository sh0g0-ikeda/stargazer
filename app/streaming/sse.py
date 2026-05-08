"""Server-Sent Events encoding helpers."""

from __future__ import annotations

import json
from collections.abc import Iterable

from app.agents.schemas import AgentEvent


def encode_sse_event(event: AgentEvent) -> str:
    """Encode one AgentEvent as an SSE message."""

    event_name = event.event_type.value.lower()
    data = {
        "run_id": event.run_id,
        "agent_path": event.agent_path,
        "seq": event.seq,
        "event_type": event_name,
        "payload": event.payload,
        "occurred_at": event.occurred_at.isoformat(),
    }
    json_data = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    return f"id: {event.seq}\nevent: {event_name}\ndata: {json_data}\n\n"


def events_since(events: Iterable[AgentEvent], last_seq: int | None) -> list[AgentEvent]:
    """Return events after the client-visible sequence id."""

    if last_seq is None:
        return sorted(events, key=lambda event: event.seq)
    return sorted((event for event in events if event.seq > last_seq), key=lambda event: event.seq)
