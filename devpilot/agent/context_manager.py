"""Context window manager: history compaction, summarization, and token budgeting."""

from devpilot.core.logging import get_logger
from devpilot.llm.base import Message, Role

logger = get_logger("devpilot.agent.context_manager")


class ContextWindowManager:
    """Manages conversational history, ensuring prompts stay within model context bounds."""

    def __init__(self, max_context_tokens: int = 32_000, trigger_ratio: float = 0.75) -> None:
        self.max_context_tokens = max_context_tokens
        self.trigger_tokens = int(max_context_tokens * trigger_ratio)

    def estimate_tokens(self, messages: list[Message]) -> int:
        """Estimates total token length of message list (~4 characters per token)."""
        total = 0
        for m in messages:
            total += 4
            if m.content:
                total += len(m.content) // 4
            if m.tool_calls:
                for tc in m.tool_calls:
                    total += 10 + (len(tc.name) + len(tc.raw_arguments or "")) // 4
        return total

    def compact_history_if_needed(
        self,
        messages: list[Message],
        modified_files: set[str],
    ) -> list[Message]:
        """Compresses intermediate conversational rounds if token count exceeds safety threshold."""
        current_tokens = self.estimate_tokens(messages)
        if current_tokens <= self.trigger_tokens or len(messages) <= 6:
            return messages

        logger.info(
            "compacting_context_history",
            current_tokens=current_tokens,
            threshold=self.trigger_tokens,
            message_count=len(messages),
        )

        # Retain: System prompt (0), Initial User prompt (1), and the most recent 4 messages
        system_msg = messages[0]
        initial_user_msg = messages[1] if len(messages) > 1 else None
        recent_messages = messages[-4:]

        # Summarize the purged middle messages
        middle_messages = messages[2:-4]
        tool_actions = []
        for m in middle_messages:
            if m.role == Role.ASSISTANT and m.tool_calls:
                for tc in m.tool_calls:
                    tool_actions.append(
                        f"- Called `{tc.name}` on `{tc.get_arguments_dict().get('path', '')}`"
                    )

        files_summary = (
            ", ".join(f"`{f}`" for f in sorted(modified_files)) if modified_files else "None"
        )
        summary_text = (
            f"[CONTEXT COMPACTED - EARLIER STEPS SUMMARIZED]\n"
            f"The conversation history was compacted to stay within context limits.\n"
            f"- Modified files so far: {files_summary}\n"
            f"- Key intermediate actions:\n"
            + ("\n".join(tool_actions[-8:]) if tool_actions else "Exploration and analysis")
        )

        summary_msg = Message(role=Role.USER, content=summary_text)

        compacted: list[Message] = [system_msg]
        if initial_user_msg and initial_user_msg != system_msg:
            compacted.append(initial_user_msg)
        compacted.append(summary_msg)
        compacted.extend(recent_messages)

        logger.info(
            "context_compacted",
            new_tokens=self.estimate_tokens(compacted),
            new_message_count=len(compacted),
        )
        return compacted
