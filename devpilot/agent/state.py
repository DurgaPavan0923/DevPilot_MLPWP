"""Explicit Finite State Machine governing the agent lifecycle."""

import time
from dataclasses import dataclass, field
from typing import Any

from devpilot.core.exceptions import DevPilotError
from devpilot.core.types import AgentStateEnum

VALID_TRANSITIONS: dict[AgentStateEnum, set[AgentStateEnum]] = {
    AgentStateEnum.INIT: {AgentStateEnum.ANALYZE, AgentStateEnum.PLAN, AgentStateEnum.FAILED},
    AgentStateEnum.ANALYZE: {AgentStateEnum.RETRIEVE, AgentStateEnum.PLAN, AgentStateEnum.FAILED},
    AgentStateEnum.RETRIEVE: {AgentStateEnum.PLAN, AgentStateEnum.FAILED},
    AgentStateEnum.PLAN: {
        AgentStateEnum.ACT,
        AgentStateEnum.VERIFY,
        AgentStateEnum.DONE,
        AgentStateEnum.FAILED,
    },
    AgentStateEnum.ACT: {AgentStateEnum.OBSERVE, AgentStateEnum.RECOVER, AgentStateEnum.FAILED},
    AgentStateEnum.OBSERVE: {
        AgentStateEnum.ACT,
        AgentStateEnum.PLAN,
        AgentStateEnum.RECOVER,
        AgentStateEnum.VERIFY,
        AgentStateEnum.DONE,
        AgentStateEnum.FAILED,
    },
    AgentStateEnum.RECOVER: {
        AgentStateEnum.PLAN,
        AgentStateEnum.ACT,
        AgentStateEnum.RETRIEVE,
        AgentStateEnum.FAILED,
    },
    AgentStateEnum.VERIFY: {
        AgentStateEnum.DONE,
        AgentStateEnum.RECOVER,
        AgentStateEnum.PLAN,
        AgentStateEnum.FAILED,
    },
    AgentStateEnum.DONE: set(),
    AgentStateEnum.FAILED: set(),
}


@dataclass
class AgentStateData:
    session_id: str
    current_state: AgentStateEnum = AgentStateEnum.INIT
    step: int = 0
    total_prompt_tokens: int = 0
    total_completion_tokens: int = 0
    total_cost_usd: float = 0.0
    start_time: float = field(default_factory=time.monotonic)
    modified_files: set[str] = field(default_factory=set)
    created_files: set[str] = field(default_factory=set)
    recoveries_count: int = 0
    is_paused: bool = False
    pending_approval: dict[str, Any] | None = None


class AgentStateMachine:
    """Manages FSM state transitions and guarantees lifecycle invariants."""

    def __init__(self, session_id: str) -> None:
        self.data = AgentStateData(session_id=session_id)
        self.history: list[AgentStateEnum] = [AgentStateEnum.INIT]

    @property
    def current_state(self) -> AgentStateEnum:
        return self.data.current_state

    def transition(self, next_state: AgentStateEnum, reason: str = "") -> None:
        """Transitions to the next state, verifying transition legality."""
        curr = self.data.current_state
        allowed = VALID_TRANSITIONS.get(curr, set())

        if next_state not in allowed:
            raise DevPilotError(
                f"Illegal state transition from {curr.value} to {next_state.value}. Allowed: {[s.value for s in allowed]}",
                code="INVALID_STATE_TRANSITION",
                details={"from": curr.value, "to": next_state.value, "reason": reason},
            )

        self.data.current_state = next_state
        self.history.append(next_state)

    def is_terminal(self) -> bool:
        """True if agent has reached a terminal state (DONE or FAILED)."""
        return self.data.current_state in (AgentStateEnum.DONE, AgentStateEnum.FAILED)
