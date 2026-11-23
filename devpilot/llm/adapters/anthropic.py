"""Anthropic Claude provider adapter with native tool calling and SSE streaming."""

import contextlib
import json
from collections.abc import AsyncIterator
from typing import Any

import httpx

from devpilot.core.exceptions import (
    LLMAuthenticationError,
    LLMContextLengthExceededError,
    LLMError,
    LLMProviderUnavailableError,
    LLMRateLimitError,
)
from devpilot.llm.base import (
    ChatResponse,
    LLMProvider,
    Message,
    Role,
    StreamChunk,
    TokenUsage,
    ToolCall,
    ToolDefinition,
)
from devpilot.llm.cost import calculate_cost


class AnthropicProvider(LLMProvider):
    """Adapter for official Anthropic Claude /v1/messages endpoint."""

    def __init__(
        self,
        model: str = "claude-3-5-sonnet-20241022",
        api_key: str | None = None,
        base_url: str = "https://api.anthropic.com/v1",
        timeout_sec: float = 60.0,
        **kwargs: Any,
    ) -> None:
        super().__init__(model=model, api_key=api_key, **kwargs)
        self.base_url = base_url.rstrip("/")
        self.timeout_sec = timeout_sec

    @property
    def provider_name(self) -> str:
        return "anthropic"

    def _get_headers(self) -> dict[str, str]:
        if not self.api_key:
            raise LLMAuthenticationError(
                "Anthropic API key is missing or not provided", provider="anthropic"
            )
        return {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }

    def _format_messages_and_system(
        self, messages: list[Message]
    ) -> tuple[str | None, list[dict[str, Any]]]:
        system_prompts: list[str] = []
        anthropic_messages: list[dict[str, Any]] = []

        for m in messages:
            if m.role == Role.SYSTEM:
                if m.content:
                    system_prompts.append(m.content)
            elif m.role == Role.USER:
                anthropic_messages.append({"role": "user", "content": m.content or ""})
            elif m.role == Role.ASSISTANT:
                content_blocks: list[dict[str, Any]] = []
                if m.content:
                    content_blocks.append({"type": "text", "text": m.content})
                if m.tool_calls:
                    for tc in m.tool_calls:
                        content_blocks.append(
                            {
                                "type": "tool_use",
                                "id": tc.id,
                                "name": tc.name,
                                "input": tc.arguments,
                            }
                        )
                anthropic_messages.append(
                    {
                        "role": "assistant",
                        "content": content_blocks if content_blocks else "",
                    }
                )
            elif m.role == Role.TOOL:
                anthropic_messages.append(
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "tool_result",
                                "tool_use_id": m.tool_call_id or "",
                                "content": m.content or "",
                            }
                        ],
                    }
                )

        system_str = "\n\n".join(system_prompts) if system_prompts else None
        return system_str, anthropic_messages

    def _handle_error(self, exc: httpx.HTTPStatusError) -> None:
        code = exc.response.status_code
        try:
            body = exc.response.json()
            err_msg = body.get("error", {}).get("message", exc.response.text)
        except Exception:
            err_msg = exc.response.text

        if code == 401:
            raise LLMAuthenticationError(
                f"Anthropic authentication failed: {err_msg}",
                provider="anthropic",
                model=self.model,
            )
        elif code in (429, 529):
            retry_after = None
            if "retry-after" in exc.response.headers:
                with contextlib.suppress(ValueError):
                    retry_after = float(exc.response.headers["retry-after"])
            raise LLMRateLimitError(
                f"Anthropic rate limit or overloaded: {err_msg}",
                provider="anthropic",
                model=self.model,
                retry_after=retry_after,
            )
        elif code == 400 and "prompt is too long" in err_msg.lower():
            raise LLMContextLengthExceededError(
                f"Anthropic context length exceeded: {err_msg}",
                provider="anthropic",
                model=self.model,
            )
        elif code >= 500:
            raise LLMProviderUnavailableError(
                f"Anthropic service unavailable ({code}): {err_msg}",
                provider="anthropic",
                model=self.model,
            )
        raise LLMError(
            f"Anthropic error ({code}): {err_msg}",
            provider="anthropic",
            model=self.model,
            status_code=code,
        )

    async def chat(
        self,
        messages: list[Message],
        tools: list[ToolDefinition] | None = None,
        temperature: float = 0.0,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> ChatResponse:
        system_str, formatted_msgs = self._format_messages_and_system(messages)
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": formatted_msgs,
            "max_tokens": max_tokens or 4096,
            "temperature": temperature,
        }
        if system_str:
            payload["system"] = system_str
        if tools:
            payload["tools"] = [t.to_anthropic_schema() for t in tools]

        async with httpx.AsyncClient(timeout=self.timeout_sec) as client:
            try:
                resp = await client.post(
                    f"{self.base_url}/messages",
                    headers=self._get_headers(),
                    json=payload,
                )
                resp.raise_for_status()
            except httpx.HTTPStatusError as exc:
                self._handle_error(exc)
            except (httpx.ConnectError, httpx.TimeoutException) as exc:
                raise LLMProviderUnavailableError(
                    f"Anthropic connection error: {exc}", provider="anthropic", model=self.model
                ) from exc

        data = resp.json()
        content_blocks = data.get("content", [])
        text_parts: list[str] = []
        tool_calls: list[ToolCall] | None = None

        for block in content_blocks:
            b_type = block.get("type")
            if b_type == "text":
                text_parts.append(block.get("text", ""))
            elif b_type == "tool_use":
                if tool_calls is None:
                    tool_calls = []
                args = block.get("input", {})
                tool_calls.append(
                    ToolCall(
                        id=block.get("id", ""),
                        name=block.get("name", ""),
                        arguments=args if isinstance(args, dict) else {},
                        raw_arguments=json.dumps(args),
                    )
                )

        parsed_usage = data.get("usage", {})
        prompt_tokens = parsed_usage.get("input_tokens", 0)
        completion_tokens = parsed_usage.get("output_tokens", 0)
        cached_tokens = parsed_usage.get("cache_read_input_tokens", 0)
        usage = TokenUsage.compute(prompt_tokens, completion_tokens, cached=cached_tokens)
        cost = calculate_cost(
            self.provider_name, self.model, prompt_tokens, completion_tokens, cached_tokens
        )

        assistant_msg = Message(
            role=Role.ASSISTANT,
            content="".join(text_parts) if text_parts else None,
            tool_calls=tool_calls,
        )

        return ChatResponse(
            message=assistant_msg,
            finish_reason=data.get("stop_reason"),
            usage=usage,
            cost_usd=cost,
            provider=self.provider_name,
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
        system_str, formatted_msgs = self._format_messages_and_system(messages)
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": formatted_msgs,
            "max_tokens": max_tokens or 4096,
            "temperature": temperature,
            "stream": True,
        }
        if system_str:
            payload["system"] = system_str
        if tools:
            payload["tools"] = [t.to_anthropic_schema() for t in tools]

        async with httpx.AsyncClient(timeout=self.timeout_sec) as client:
            try:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/messages",
                    headers=self._get_headers(),
                    json=payload,
                ) as response:
                    if response.status_code != 200:
                        await response.aread()
                        response.raise_for_status()

                    current_tool_id: str | None = None
                    current_tool_name: str | None = None
                    current_tool_json: str = ""
                    accumulated_tools: list[ToolCall] = []

                    async for line in response.aiter_lines():
                        if not line or not line.startswith("data:"):
                            continue
                        data_str = line[5:].strip()
                        try:
                            event_data = json.loads(data_str)
                        except Exception:
                            continue

                        event_type = event_data.get("type")
                        if event_type == "content_block_start":
                            block = event_data.get("content_block", {})
                            if block.get("type") == "tool_use":
                                current_tool_id = block.get("id")
                                current_tool_name = block.get("name")
                                current_tool_json = ""
                        elif event_type == "content_block_delta":
                            delta = event_data.get("delta", {})
                            delta_type = delta.get("type")
                            if delta_type == "text_delta":
                                yield StreamChunk(delta_text=delta.get("text", ""))
                            elif delta_type == "input_json_delta":
                                current_tool_json += delta.get("partial_json", "")
                        elif event_type == "content_block_stop":
                            if current_tool_id and current_tool_name:
                                try:
                                    args = json.loads(current_tool_json)
                                except Exception:
                                    args = {}
                                tc = ToolCall(
                                    id=current_tool_id,
                                    name=current_tool_name,
                                    arguments=args,
                                    raw_arguments=current_tool_json,
                                )
                                accumulated_tools.append(tc)
                                current_tool_id = None
                                current_tool_name = None
                        elif event_type == "message_delta":
                            delta_stop = event_data.get("delta", {}).get("stop_reason")
                            u = event_data.get("usage", {})
                            yield StreamChunk(
                                delta_tool_calls=accumulated_tools if accumulated_tools else None,
                                finish_reason=delta_stop,
                                usage=TokenUsage.compute(
                                    u.get("input_tokens", 0),
                                    u.get("output_tokens", 0),
                                )
                                if u
                                else None,
                            )
            except httpx.HTTPStatusError as exc:
                self._handle_error(exc)
            except (httpx.ConnectError, httpx.TimeoutException) as exc:
                raise LLMProviderUnavailableError(
                    f"Anthropic connection error: {exc}", provider="anthropic", model=self.model
                ) from exc

    def count_tokens(self, text_or_messages: str | list[Message]) -> int:
        if isinstance(text_or_messages, str):
            return max(1, len(text_or_messages) // 4)
        total = 0
        for m in text_or_messages:
            total += 4
            if m.content:
                total += len(m.content) // 4
            if m.tool_calls:
                total += len(m.tool_calls) * 12
        return total
