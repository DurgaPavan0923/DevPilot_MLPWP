"""Recovery policy with global retry caps, per-signature caps, and an escalation ladder."""

from dataclasses import dataclass
from enum import IntEnum
from typing import Any

from devpilot.core.types import ErrorTypeEnum, ToolResult
from devpilot.recovery.classifier import ErrorClassifier
from devpilot.recovery.hasher import ErrorSignatureHasher
from devpilot.recovery.loop_detector import LoopDetector


class EscalationLevel(IntEnum):
    RETRY_WITH_CONTEXT = 1
    RE_RETRIEVE_CONTEXT = 2
    SWITCH_APPROACH = 3
    REDUCE_SCOPE = 4
    ABORT = 5


@dataclass
class RecoveryAction:
    level: EscalationLevel
    error_type: ErrorTypeEnum
    error_signature: str
    feedback_message: str
    should_abort: bool = False
    re_retrieve_query: str | None = None


class RecoveryPolicy:
    """Bounded recovery policy enforcing retry quotas and escalation strategies."""

    def __init__(
        self,
        global_retry_cap: int = 5,
        per_signature_cap: int = 2,
    ) -> None:
        self.global_retry_cap = global_retry_cap
        self.per_signature_cap = per_signature_cap
        self.total_recoveries: int = 0
        self.signature_counts: dict[str, int] = {}
        self.loop_detector = LoopDetector(repetition_threshold=3)

    def handle_tool_error(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        tool_result: ToolResult,
    ) -> RecoveryAction:
        """Evaluates tool execution failure and determines escalation ladder action."""
        self.total_recoveries += 1

        # 1. Classify error and hash signature
        err_type = tool_result.error_type or ErrorClassifier.classify(
            tool_result.output, tool_result.exit_code
        )
        sig = ErrorSignatureHasher.hash_error(tool_result.output)

        self.signature_counts[sig] = self.signature_counts.get(sig, 0) + 1
        sig_count = self.signature_counts[sig]

        # Record for loop detection
        self.loop_detector.record_action(tool_name, arguments)
        self.loop_detector.record_error(sig)

        is_action_loop, action_reason = self.loop_detector.is_action_looping()
        is_error_loop, error_reason = self.loop_detector.is_error_looping()

        # Check hard loop break
        if is_action_loop or is_error_loop:
            reason = action_reason or error_reason
            return RecoveryAction(
                level=EscalationLevel.ABORT,
                error_type=err_type,
                error_signature=sig,
                feedback_message=f"ABORT: {reason} Stopping execution to prevent infinite oscillation.",
                should_abort=True,
            )

        # Check retry limits
        if self.total_recoveries > self.global_retry_cap:
            return RecoveryAction(
                level=EscalationLevel.ABORT,
                error_type=err_type,
                error_signature=sig,
                feedback_message=(
                    f"ABORT: Global recovery limit ({self.global_retry_cap}) reached.\n"
                    f"Last error ({err_type.value}): {tool_result.output[:300]}"
                ),
                should_abort=True,
            )

        # Determine escalation tier
        if sig_count > self.per_signature_cap:
            # Per-signature cap exceeded: Force approach switch or scope reduction
            level = (
                EscalationLevel.SWITCH_APPROACH
                if self.total_recoveries < self.global_retry_cap - 1
                else EscalationLevel.REDUCE_SCOPE
            )
        elif self.total_recoveries == 1:
            level = EscalationLevel.RETRY_WITH_CONTEXT
        elif self.total_recoveries == 2:
            level = EscalationLevel.RE_RETRIEVE_CONTEXT
        elif self.total_recoveries == 3:
            level = EscalationLevel.SWITCH_APPROACH
        elif self.total_recoveries == 4:
            level = EscalationLevel.REDUCE_SCOPE
        else:
            level = EscalationLevel.ABORT

        # Craft structured feedback for LLM
        feedback = self._build_feedback(level, err_type, tool_name, tool_result.output, sig_count)

        re_query = None
        if level == EscalationLevel.RE_RETRIEVE_CONTEXT:
            re_query = f"{tool_name} error: {tool_result.output[:120]}"

        return RecoveryAction(
            level=level,
            error_type=err_type,
            error_signature=sig,
            feedback_message=feedback,
            should_abort=False,
            re_retrieve_query=re_query,
        )

    def _build_feedback(
        self,
        level: EscalationLevel,
        error_type: ErrorTypeEnum,
        tool_name: str,
        output: str,
        sig_count: int,
    ) -> str:
        summary_error = output[:600]

        if level == EscalationLevel.RETRY_WITH_CONTEXT:
            return (
                f"[RECOVERY LEVEL 1 - TARGETED CORRECTION]\n"
                f"Tool '{tool_name}' failed with {error_type.value} error (attempt {sig_count}):\n"
                f"```\n{summary_error}\n```\n"
                f"Instruction: Inspect the failure reason carefully and correct the input arguments."
            )
        elif level == EscalationLevel.RE_RETRIEVE_CONTEXT:
            return (
                f"[RECOVERY LEVEL 2 - RE-RETRIEVING REPOSITORY CONTEXT]\n"
                f"Tool '{tool_name}' failed repeatedly with error:\n"
                f"```\n{summary_error}\n```\n"
                f"Instruction: Fresh repository context has been re-indexed. Re-examine the surrounding code structure."
            )
        elif level == EscalationLevel.SWITCH_APPROACH:
            return (
                f"[RECOVERY LEVEL 3 - SWITCH APPROACH]\n"
                f"The current modification strategy has failed {sig_count} times on '{tool_name}':\n"
                f"```\n{summary_error}\n```\n"
                f"Instruction: STOP repeating this edit. Discard this approach, inspect alternative files or methods, and replan."
            )
        elif level == EscalationLevel.REDUCE_SCOPE:
            return (
                f"[RECOVERY LEVEL 4 - SCOPE REDUCTION]\n"
                f"Critical repeated failures encountered:\n"
                f"```\n{summary_error}\n```\n"
                f"Instruction: Narrow your objective to the minimal viable fix that restores tests to a passing state."
            )
        return f"[RECOVERY - ERROR]: {summary_error}"
