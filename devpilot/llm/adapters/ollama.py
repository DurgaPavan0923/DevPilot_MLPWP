"""Ollama local model adapter with streaming and JSON/XML fallback tool-calling."""

import json
from collections.abc import AsyncIterator
from typing import Any

import httpx

from devpilot.core.exceptions import LLMError, LLMProviderUnavailableError
from devpilot.llm.base import (
    ChatResponse,
    LLMProvider,
    Message,
    Role,
    StreamChunk,
    TokenUsage,
    ToolDefinition,
)
from devpilot.llm.fallback import inject_tool_instructions, parse_fallback_tool_calls


class OllamaProvider(LLMProvider):
    """Adapter for locally hosted Ollama instances."""

    def __init__(
        self,
        model: str = "deepseek-coder:6.7b",
        base_url: str = "http://localhost:11434",
        timeout_sec: float = 120.0,
        api_key: str | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(model=model, api_key=api_key, **kwargs)
        self.base_url = base_url.rstrip("/")
        self.timeout_sec = timeout_sec

    @property
    def provider_name(self) -> str:
        return "ollama"

    @property
    def supports_native_tools(self) -> bool:
        return False

    def _format_messages(self, messages: list[Message]) -> list[dict[str, str]]:
        formatted = []
        for m in messages:
            role_str = "user" if m.role == Role.TOOL else m.role.value
            content = m.content or ""
            if m.tool_calls:
                # Format assistant tool calls into readable text
                tc_texts = [
                    f"<tool_call>{json.dumps({'name': tc.name, 'arguments': tc.arguments})}</tool_call>"
                    for tc in m.tool_calls
                ]
                content = f"{content}\n" + "\n".join(tc_texts)
            formatted.append({"role": role_str, "content": content.strip()})
        return formatted

    async def chat(
        self,
        messages: list[Message],
        tools: list[ToolDefinition] | None = None,
        temperature: float = 0.0,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> ChatResponse:
        effective_messages = messages
        if tools:
            effective_messages = inject_tool_instructions(messages, tools)

        payload: dict[str, Any] = {
            "model": self.model,
            "messages": self._format_messages(effective_messages),
            "stream": False,
            "options": {
                "temperature": temperature,
            },
        }
        if max_tokens:
            payload["options"]["num_predict"] = max_tokens

        async with httpx.AsyncClient(timeout=self.timeout_sec) as client:
            try:
                resp = await client.post(f"{self.base_url}/api/chat", json=payload)
                resp.raise_for_status()
            except httpx.HTTPStatusError as exc:
                raise LLMError(
                    f"Ollama server error ({exc.response.status_code}): {exc.response.text}",
                    provider="ollama",
                    model=self.model,
                ) from exc
            except (httpx.ConnectError, httpx.TimeoutException) as exc:
                raise LLMProviderUnavailableError(
                    f"Cannot connect to Ollama at {self.base_url}. Ensure Ollama is running.",
                    provider="ollama",
                    model=self.model,
                ) from exc

        data = resp.json()
        raw_content = data.get("message", {}).get("content", "")

        # Parse tool calls using fallback parser
        cleaned_text, tool_calls = parse_fallback_tool_calls(raw_content)

        prompt_tokens = data.get("prompt_eval_count", self.count_tokens(effective_messages))
        completion_tokens = data.get("eval_count", self.count_tokens(raw_content))
        usage = TokenUsage.compute(prompt_tokens, completion_tokens)

        assistant_msg = Message(
            role=Role.ASSISTANT,
            content=cleaned_text,
            tool_calls=tool_calls,
        )

        return ChatResponse(
            message=assistant_msg,
            finish_reason="stop" if not tool_calls else "tool_calls",
            usage=usage,
            cost_usd=0.0,
            provider="ollama",
            model=self.model,
            raw_response=data,
        )

    async def stream(
        self,
        messages: list[Message],
        tools: list[ToolDefinition] | None = None,
        temperature: float = 0.0,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[StreamChunk]:
        effective_messages = messages
        if tools:
            effective_messages = inject_tool_instructions(messages, tools)

        payload: dict[str, Any] = {
            "model": self.model,
            "messages": self._format_messages(effective_messages),
            "stream": True,
            "options": {
                "temperature": temperature,
            },
        }
        if max_tokens:
            payload["options"]["num_predict"] = max_tokens

        accumulated_text = ""

        async with httpx.AsyncClient(timeout=self.timeout_sec) as client:
            try:
                async with client.stream(
                    "POST", f"{self.base_url}/api/chat", json=payload
                ) as response:
                    if response.status_code != 200:
                        await response.aread()
                        response.raise_for_status()

                    async for line in response.aiter_lines():
                        if not line:
                            continue
                        try:
                            chunk_data = json.loads(line)
                        except Exception:
                            continue

                        part = chunk_data.get("message", {}).get("content", "")
                        if part:
                            accumulated_text += part
                            yield StreamChunk(delta_text=part)

                        if chunk_data.get("done", False):
                            # Final chunk: check if accumulated text contains tool calls
                            cleaned, tool_calls = parse_fallback_tool_calls(accumulated_text)
                            p_toks = chunk_data.get("prompt_eval_count", 0)
                            c_toks = chunk_data.get("eval_count", 0)
                            yield StreamChunk(
                                delta_tool_calls=tool_calls,
                                finish_reason="stop",
                                usage=TokenUsage.compute(p_toks, c_toks),
                            )
            except httpx.HTTPStatusError as exc:
                raise LLMError(
                    f"Ollama stream error: {exc}", provider="ollama", model=self.model
                ) from exc
            except (httpx.ConnectError, httpx.TimeoutException) as exc:
                raise LLMProviderUnavailableError(
                    f"Ollama stream connection error: {exc}", provider="ollama", model=self.model
                ) from exc

    def count_tokens(self, text_or_messages: str | list[Message]) -> int:
        if isinstance(text_or_messages, str):
            return max(1, len(text_or_messages.split()))
        total = 0
        for m in text_or_messages:
            total += 4
            if m.content:
                total += len(m.content.split())
        return total
