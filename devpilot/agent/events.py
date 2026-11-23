"""Typed streaming event contracts emitted by the agent runtime."""

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class AgentEventType(StrEnum):
    THOUGHT = "thought"
    RETRIEVAL = "retrieval"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    ERROR = "error"
    RECOVERY = "recovery"
    APPROVAL_REQUEST = "approval_request"
    STATE_CHANGE = "state_change"
    USAGE = "usage"
    FINAL = "final"


class AgentEvent(BaseModel):
    """Standardized event packet broadcast over SSE / WebSocket to listeners."""

    type: AgentEventType = Field(...)
    session_id: str = Field(...)
    step: int = Field(default=0, ge=0)
    data: dict[str, Any] = Field(default_factory=dict)
    timestamp: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())

    def to_sse_line(self) -> str:
        """Formats the event as an SSE formatted string."""
        import json

        payload = json.dumps(self.model_dump())
        return f"event: {self.type.value}\ndata: {payload}\n\n"
