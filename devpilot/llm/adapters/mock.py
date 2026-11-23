"""Deterministic Mock Provider for unit testing, CI pipelines, and offline evaluation."""

import asyncio
import uuid
from collections.abc import AsyncIterator
from typing import Any

from devpilot.llm.base import (
    ChatResponse,
    LLMProvider,
    Message,
    StreamChunk,
    TokenUsage,
    ToolCall,
    ToolDefinition,
)


class MockProvider(LLMProvider):
    """Fully programmable mock LLM provider for deterministic assertions and tests."""

    def __init__(
        self,
        model: str = "mock-model",
        api_key: str | None = "mock-key",
        latency_sec: float = 0.0,
        **kwargs: Any,
    ) -> None:
        super().__init__(model=model, api_key=api_key, **kwargs)
        self.latency_sec = latency_sec
        self.recorded_calls: list[dict[str, Any]] = []
        self._queued_responses: list[ChatResponse] = []
        self._queued_stream_chunks: list[list[StreamChunk]] = []
        self._queued_exceptions: list[Exception] = []

    @property
    def provider_name(self) -> str:
        return "mock"

    def queue_response(
        self,
        content: str | None = None,
        tool_calls: list[ToolCall] | None = None,
        finish_reason: str = "stop",
        prompt_tokens: int = 10,
        completion_tokens: int = 10,
    ) -> None:
        """Enqueues a deterministic response to be returned by next chat() call."""
        msg = Message.assistant(content=content, tool_calls=tool_calls)
        usage = TokenUsage.compute(prompt_tokens, completion_tokens)
        resp = ChatResponse(
            message=msg,
            finish_reason=finish_reason,
            usage=usage,
            cost_usd=0.0,
            provider="mock",
            model=self.model,
        )
        self._queued_responses.append(resp)

    def queue_tool_call(
        self,
        name: str,
        arguments: dict[str, Any],
        content: str | None = None,
    ) -> None:
        """Convenience method to queue a tool invocation response."""
        tc = ToolCall(
            id=f"call_{uuid.uuid4().hex[:8]}",
            name=name,
            arguments=arguments,
        )
        self.queue_response(content=content, tool_calls=[tc], finish_reason="tool_calls")

    def queue_exception(self, exc: Exception) -> None:
        """Enqueues an exception to be raised on the next invocation."""
        self._queued_exceptions.append(exc)

    def queue_stream_chunks(self, chunks: list[StreamChunk]) -> None:
        """Enqueues a sequence of stream chunks."""
        self._queued_stream_chunks.append(chunks)

    async def chat(
        self,
        messages: list[Message],
        tools: list[ToolDefinition] | None = None,
        temperature: float = 0.0,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> ChatResponse:
        self.recorded_calls.append(
            {
                "messages": messages,
                "tools": tools,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "kwargs": kwargs,
            }
        )

        if self.latency_sec > 0:
            await asyncio.sleep(self.latency_sec)

        if self._queued_exceptions:
            raise self._queued_exceptions.pop(0)

        if self._queued_responses:
            return self._queued_responses.pop(0)

        # Default synthetic response
        last_msg = (messages[-1].content or "") if messages else ""
        prompt_toks = self.count_tokens(messages)
        content = f"Mock response to: {last_msg[:60]}"
        comp_toks = len(content.split())
        return ChatResponse(
            message=Message.assistant(content=content),
            finish_reason="stop",
            usage=TokenUsage.compute(prompt_toks, comp_toks),
            cost_usd=0.0,
            provider="mock",
            model=self.model,
        )

    async def stream(
        self,
        messages: list[Message],
        tools: list[ToolDefinition] | None = None,
        temperature: float = 0.0,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[StreamChunk]:
        self.recorded_calls.append(
            {
                "messages": messages,
                "tools": tools,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "stream": True,
                "kwargs": kwargs,
            }
        )

        if self.latency_sec > 0:
            await asyncio.sleep(self.latency_sec)

        if self._queued_exceptions:
            raise self._queued_exceptions.pop(0)

        if self._queued_stream_chunks:
            for chunk in self._queued_stream_chunks.pop(0):
                yield chunk
            return

        # Default streaming words
        text = "Mock streaming assistant output token stream"
        tokens = text.split()
        for i, token in enumerate(tokens):
            delta = token + (" " if i < len(tokens) - 1 else "")
            yield StreamChunk(delta_text=delta)
            if self.latency_sec > 0:
                await asyncio.sleep(self.latency_sec / max(1, len(tokens)))

        yield StreamChunk(
            finish_reason="stop",
            usage=TokenUsage.compute(self.count_tokens(messages), len(tokens)),
        )

    def count_tokens(self, text_or_messages: str | list[Message]) -> int:
        if isinstance(text_or_messages, str):
            return max(1, len(text_or_messages.split()))
        total = 0
        for m in text_or_messages:
            total += 4  # overhead
            if m.content:
                total += len(m.content.split())
            if m.tool_calls:
                total += len(m.tool_calls) * 10
        return total
