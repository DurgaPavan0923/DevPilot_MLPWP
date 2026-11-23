"""Execution loop and repeating error cycle detector."""

import hashlib
import json
from typing import Any


class LoopDetector:
    """Detects infinite loops in action calls, error signatures, or alternating state cycles."""

    def __init__(self, repetition_threshold: int = 3) -> None:
        self.repetition_threshold = repetition_threshold
        self.action_history: list[str] = []
        self.signature_history: list[str] = []

    def record_action(self, tool_name: str, arguments: dict[str, Any]) -> None:
        """Records a tool invocation signature."""
        try:
            arg_str = json.dumps(arguments, sort_keys=True)
        except Exception:
            arg_str = str(arguments)
        action_key = f"{tool_name}:{hashlib.sha256(arg_str.encode()).hexdigest()[:8]}"
        self.action_history.append(action_key)

    def record_error(self, error_signature: str) -> None:
        """Records an error signature."""
        self.signature_history.append(error_signature)

    def is_action_looping(self) -> tuple[bool, str | None]:
        """Checks if the same tool action has been called repeatedly consecutively."""
        if len(self.action_history) < self.repetition_threshold:
            return False, None

        last_action = self.action_history[-1]
        tail = self.action_history[-self.repetition_threshold :]
        if all(a == last_action for a in tail):
            return (
                True,
                f"Action loop detected: action '{last_action}' executed {self.repetition_threshold} times identically.",
            )

        # Alternating ping-pong cycle: A -> B -> A -> B
        if (
            len(self.action_history) >= 4
            and self.action_history[-1] == self.action_history[-3]
            and self.action_history[-2] == self.action_history[-4]
            and self.action_history[-1] != self.action_history[-2]
        ):
            return (
                True,
                "Alternating cycle loop detected: agent is ping-ponging between two alternating actions.",
            )

        return False, None

    def is_error_looping(self) -> tuple[bool, str | None]:
        """Checks if the same error signature has occurred repeatedly."""
        if len(self.signature_history) < self.repetition_threshold:
            return False, None

        last_sig = self.signature_history[-1]
        count = sum(
            1 for s in self.signature_history[-self.repetition_threshold :] if s == last_sig
        )
        if count >= self.repetition_threshold:
            return (
                True,
                f"Error loop detected: error signature '{last_sig}' triggered {count} times consecutively.",
            )

        return False, None
