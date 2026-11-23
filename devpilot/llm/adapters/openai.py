"""OpenAI API provider adapter with native tool calling and SSE streaming."""

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


class OpenAIProvider(LLMProvider):
    """Adapter for official OpenAI /v1/chat/completions endpoint."""

    def __init__(
        self,
        model: str = "gpt-4o-mini",
        api_key: str | None = None,
        base_url: str = "https://api.openai.com/v1",
        timeout_sec: float = 60.0,
        **kwargs: Any,
    ) -> None:
        super().__init__(model=model, api_key=api_key, **kwargs)
        self.base_url = base_url.rstrip("/")
        self.timeout_sec = timeout_sec

    @property
    def provider_name(self) -> str:
        return "openai"

    def _get_headers(self) -> dict[str, str]:
        if not self.api_key:
            raise LLMAuthenticationError(
                "OpenAI API key is missing or not provided", provider="openai"
            )
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _format_messages(self, messages: list[Message]) -> list[dict[str, Any]]:
        formatted = []
        for m in messages:
            entry: dict[str, Any] = {"role": m.role.value}
            if m.content is not None:
                entry["content"] = m.content
            if m.name:
                entry["name"] = m.name
            if m.tool_call_id:
                entry["tool_call_id"] = m.tool_call_id
            if m.tool_calls:
                entry["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.name,
                            "arguments": tc.raw_arguments or json.dumps(tc.arguments),
                        },
                    }
                    for tc in m.tool_calls
                ]
            formatted.append(entry)
        return formatted

    def _handle_error(self, exc: httpx.HTTPStatusError) -> None:
        code = exc.response.status_code
        try:
            body = exc.response.json()
            err_msg = body.get("error", {}).get("message", exc.response.text)
        except Exception:
            err_msg = exc.response.text

        if code == 401:
            raise LLMAuthenticationError(
                f"OpenAI authentication failed: {err_msg}", provider="openai", model=self.model
            )
        elif code == 429:
            retry_after = None
            if "Retry-After" in exc.response.headers:
                with contextlib.suppress(ValueError):
                    retry_after = float(exc.response.headers["Retry-After"])
            raise LLMRateLimitError(
                f"OpenAI rate limit: {err_msg}",
                provider="openai",
                model=self.model,
                retry_after=retry_after,
            )
        elif code == 400 and "context_length_exceeded" in err_msg.lower():
            raise LLMContextLengthExceededError(
                f"OpenAI context exceeded: {err_msg}", provider="openai", model=self.model
            )
        elif code >= 500:
            raise LLMProviderUnavailableError(
                f"OpenAI service unavailable ({code}): {err_msg}",
                provider="openai",
                model=self.model,
            )
        raise LLMError(
            f"OpenAI error ({code}): {err_msg}",
            provider="openai",
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
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": self._format_messages(messages),
            "temperature": temperature,
        }
        if max_tokens:
            payload["max_tokens"] = max_tokens
        if tools:
            payload["tools"] = [t.to_openai_schema() for t in tools]
            payload["tool_choice"] = kwargs.get("tool_choice", "auto")

        async with httpx.AsyncClient(timeout=self.timeout_sec) as client:
            try:
                resp = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=self._get_headers(),
                    json=payload,
                )
                resp.raise_for_status()
            except httpx.HTTPStatusError as exc:
                self._handle_error(exc)
            except (httpx.ConnectError, httpx.TimeoutException) as exc:
                raise LLMProviderUnavailableError(
                    f"OpenAI connection error: {exc}", provider="openai", model=self.model
                ) from exc

        data = resp.json()
        choice = data["choices"][0]
        choice_msg = choice["message"]

        # Parse tool calls if present
        tool_calls: list[ToolCall] | None = None
        if "tool_calls" in choice_msg and choice_msg["tool_calls"]:
            tool_calls = []
            for tc in choice_msg["tool_calls"]:
                fn = tc.get("function", {})
                raw_args = fn.get("arguments", "{}")
                try:
                    args = json.loads(raw_args)
                except Exception:
                    args = {}
                tool_calls.append(
                    ToolCall(
                        id=tc.get("id", ""),
                        name=fn.get("name", ""),
                        arguments=args,
                        raw_arguments=raw_args,
                    )
                )

        parsed_usage = data.get("usage", {})
        prompt_tokens = parsed_usage.get("prompt_tokens", 0)
        completion_tokens = parsed_usage.get("completion_tokens", 0)
        cached_tokens = parsed_usage.get("prompt_tokens_details", {}).get("cached_tokens", 0)
        usage = TokenUsage.compute(prompt_tokens, completion_tokens, cached=cached_tokens)
        cost = calculate_cost(
            self.provider_name, self.model, prompt_tokens, completion_tokens, cached_tokens
        )

        assistant_msg = Message(
            role=Role.ASSISTANT,
            content=choice_msg.get("content"),
            tool_calls=tool_calls,
        )

        return ChatResponse(
            message=assistant_msg,
            finish_reason=choice.get("finish_reason"),
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
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": self._format_messages(messages),
            "temperature": temperature,
            "stream": True,
            "stream_options": {"include_usage": True},
        }
        if max_tokens:
            payload["max_tokens"] = max_tokens
        if tools:
            payload["tools"] = [t.to_openai_schema() for t in tools]
            payload["tool_choice"] = kwargs.get("tool_choice", "auto")

        async with httpx.AsyncClient(timeout=self.timeout_sec) as client:
            try:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/chat/completions",
                    headers=self._get_headers(),
                    json=payload,
                ) as response:
                    if response.status_code != 200:
                        await response.aread()
                        response.raise_for_status()

                    accumulated_tools: dict[int, dict[str, Any]] = {}
                    async for line in response.aiter_lines():
                        if not line or not line.startswith("data:"):
                            continue
                        data_str = line[5:].strip()
                        if data_str == "[DONE]":
                            break
                        try:
                            chunk_data = json.loads(data_str)
                        except Exception:
                            continue

                        chunk_usage = None
                        if "usage" in chunk_data and chunk_data["usage"]:
                            u = chunk_data["usage"]
                            chunk_usage = TokenUsage.compute(
                                u.get("prompt_tokens", 0),
                                u.get("completion_tokens", 0),
                            )

                        choices = chunk_data.get("choices", [])
                        if not choices:
                            if chunk_usage:
                                yield StreamChunk(usage=chunk_usage)
                            continue

                        delta = choices[0].get("delta", {})
                        finish_reason = choices[0].get("finish_reason")

                        # Text delta
                        delta_text = delta.get("content")

                        # Tool calls incremental delta assembly
                        delta_tools: list[ToolCall] | None = None
                        if "tool_calls" in delta and delta["tool_calls"]:
                            for tc_chunk in delta["tool_calls"]:
                                idx = tc_chunk.get("index", 0)
                                if idx not in accumulated_tools:
                                    accumulated_tools[idx] = {
                                        "id": tc_chunk.get("id", ""),
                                        "name": tc_chunk.get("function", {}).get("name", ""),
                                        "arguments": "",
                                    }
                                else:
                                    if tc_chunk.get("id"):
                                        accumulated_tools[idx]["id"] = tc_chunk["id"]
                                    if tc_chunk.get("function", {}).get("name"):
                                        accumulated_tools[idx]["name"] += tc_chunk["function"][
                                            "name"
                                        ]
                                if tc_chunk.get("function", {}).get("arguments"):
                                    accumulated_tools[idx]["arguments"] += tc_chunk["function"][
                                        "arguments"
                                    ]

                        if finish_reason == "tool_calls" or (finish_reason and accumulated_tools):
                            delta_tools = []
                            for idx, t_data in sorted(accumulated_tools.items()):
                                raw_args = t_data["arguments"]
                                try:
                                    args = json.loads(raw_args)
                                except Exception:
                                    args = {}
                                delta_tools.append(
                                    ToolCall(
                                        id=t_data["id"] or f"call_{idx}",
                                        name=t_data["name"],
                                        arguments=args,
                                        raw_arguments=raw_args,
                                    )
                                )

                        yield StreamChunk(
                            delta_text=delta_text,
                            delta_tool_calls=delta_tools,
                            finish_reason=finish_reason,
                            usage=chunk_usage,
                        )
            except httpx.HTTPStatusError as exc:
                self._handle_error(exc)
            except (httpx.ConnectError, httpx.TimeoutException) as exc:
                raise LLMProviderUnavailableError(
                    f"OpenAI connection error: {exc}", provider="openai", model=self.model
                ) from exc

    def count_tokens(self, text_or_messages: str | list[Message]) -> int:
        # Fast accurate fallback estimation: ~3.8 chars per token
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
