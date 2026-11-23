"""Google Gemini provider adapter with function calling and SSE streaming."""

import json
from collections.abc import AsyncIterator
from typing import Any

import httpx

from devpilot.core.exceptions import (
    LLMAuthenticationError,
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


class GeminiProvider(LLMProvider):
    """Adapter for Google Gemini REST API."""

    def __init__(
        self,
        model: str = "gemini-1.5-flash",
        api_key: str | None = None,
        base_url: str = "https://generativelanguage.googleapis.com/v1beta",
        timeout_sec: float = 60.0,
        **kwargs: Any,
    ) -> None:
        super().__init__(model=model, api_key=api_key, **kwargs)
        self.base_url = base_url.rstrip("/")
        self.timeout_sec = timeout_sec

    @property
    def provider_name(self) -> str:
        return "gemini"

    def _get_headers(self) -> dict[str, str]:
        if not self.api_key:
            raise LLMAuthenticationError(
                "Gemini API key is missing or not provided", provider="gemini"
            )
        return {
            "x-goog-api-key": self.api_key,
            "Content-Type": "application/json",
        }

    def _format_contents(
        self, messages: list[Message]
    ) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
        system_instruction: dict[str, Any] | None = None
        contents: list[dict[str, Any]] = []

        system_parts = []
        for m in messages:
            if m.role == Role.SYSTEM:
                if m.content:
                    system_parts.append({"text": m.content})
            elif m.role == Role.USER:
                contents.append(
                    {
                        "role": "user",
                        "parts": [{"text": m.content or ""}],
                    }
                )
            elif m.role == Role.ASSISTANT:
                parts: list[dict[str, Any]] = []
                if m.content:
                    parts.append({"text": m.content})
                if m.tool_calls:
                    for tc in m.tool_calls:
                        parts.append(
                            {
                                "functionCall": {
                                    "name": tc.name,
                                    "args": tc.arguments,
                                }
                            }
                        )
                contents.append({"role": "model", "parts": parts if parts else [{"text": ""}]})
            elif m.role == Role.TOOL:
                contents.append(
                    {
                        "role": "user",
                        "parts": [
                            {
                                "functionResponse": {
                                    "name": m.name or "tool",
                                    "response": {"output": m.content or ""},
                                }
                            }
                        ],
                    }
                )

        if system_parts:
            system_instruction = {"parts": system_parts}

        return system_instruction, contents

    def _format_tools(self, tools: list[ToolDefinition]) -> list[dict[str, Any]]:
        declarations = []
        for t in tools:
            declarations.append(
                {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.parameters,
                }
            )
        return [{"functionDeclarations": declarations}]

    def _handle_error(self, exc: httpx.HTTPStatusError) -> None:
        code = exc.response.status_code
        try:
            body = exc.response.json()
            err_msg = body.get("error", {}).get("message", exc.response.text)
        except Exception:
            err_msg = exc.response.text

        if code == 400 and (
            "api key not valid" in err_msg.lower() or "invalid api key" in err_msg.lower()
        ):
            raise LLMAuthenticationError(
                f"Gemini authentication failed: {err_msg}", provider="gemini", model=self.model
            )
        elif code == 429:
            raise LLMRateLimitError(
                f"Gemini rate limit exceeded: {err_msg}", provider="gemini", model=self.model
            )
        elif code >= 500:
            raise LLMProviderUnavailableError(
                f"Gemini service unavailable ({code}): {err_msg}",
                provider="gemini",
                model=self.model,
            )
        raise LLMError(
            f"Gemini error ({code}): {err_msg}",
            provider="gemini",
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
        system_inst, contents = self._format_contents(messages)
        payload: dict[str, Any] = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
            },
        }
        if max_tokens:
            payload["generationConfig"]["maxOutputTokens"] = max_tokens
        if system_inst:
            payload["systemInstruction"] = system_inst
        if tools:
            payload["tools"] = self._format_tools(tools)

        model_name = (
            self.model
            if not self.model.startswith("models/")
            else self.model.replace("models/", "")
        )
        endpoint = f"{self.base_url}/models/{model_name}:generateContent"

        async with httpx.AsyncClient(timeout=self.timeout_sec) as client:
            try:
                resp = await client.post(endpoint, headers=self._get_headers(), json=payload)
                resp.raise_for_status()
            except httpx.HTTPStatusError as exc:
                self._handle_error(exc)
            except (httpx.ConnectError, httpx.TimeoutException) as exc:
                raise LLMProviderUnavailableError(
                    f"Gemini connection error: {exc}", provider="gemini", model=self.model
                ) from exc

        data = resp.json()
        candidates = data.get("candidates", [])
        if not candidates:
            return ChatResponse(
                message=Message.assistant(content=""),
                finish_reason="empty",
                provider=self.provider_name,
                model=self.model,
                raw_response=data,
            )

        cand = candidates[0]
        content_obj = cand.get("content", {})
        parts = content_obj.get("parts", [])

        text_parts: list[str] = []
        tool_calls: list[ToolCall] | None = None

        for idx, part in enumerate(parts):
            if "text" in part:
                text_parts.append(part["text"])
            elif "functionCall" in part:
                if tool_calls is None:
                    tool_calls = []
                fc = part["functionCall"]
                fn_name = fc.get("name", "")
                args = fc.get("args", {})
                tool_calls.append(
                    ToolCall(
                        id=f"call_{idx}_{fn_name}",
                        name=fn_name,
                        arguments=args if isinstance(args, dict) else {},
                        raw_arguments=json.dumps(args),
                    )
                )

        usage_meta = data.get("usageMetadata", {})
        prompt_tokens = usage_meta.get("promptTokenCount", 0)
        completion_tokens = usage_meta.get("candidatesTokenCount", 0)
        usage = TokenUsage.compute(prompt_tokens, completion_tokens)
        cost = calculate_cost(self.provider_name, self.model, prompt_tokens, completion_tokens)

        assistant_msg = Message(
            role=Role.ASSISTANT,
            content="".join(text_parts) if text_parts else None,
            tool_calls=tool_calls,
        )

        return ChatResponse(
            message=assistant_msg,
            finish_reason=cand.get("finishReason"),
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
        system_inst, contents = self._format_contents(messages)
        payload: dict[str, Any] = {
            "contents": contents,
            "generationConfig": {"temperature": temperature},
        }
        if max_tokens:
            payload["generationConfig"]["maxOutputTokens"] = max_tokens
        if system_inst:
            payload["systemInstruction"] = system_inst
        if tools:
            payload["tools"] = self._format_tools(tools)

        model_name = (
            self.model
            if not self.model.startswith("models/")
            else self.model.replace("models/", "")
        )
        endpoint = f"{self.base_url}/models/{model_name}:streamGenerateContent?alt=sse"

        async with httpx.AsyncClient(timeout=self.timeout_sec) as client:
            try:
                async with client.stream(
                    "POST", endpoint, headers=self._get_headers(), json=payload
                ) as response:
                    if response.status_code != 200:
                        await response.aread()
                        response.raise_for_status()

                    async for line in response.aiter_lines():
                        if not line or not line.startswith("data:"):
                            continue
                        data_str = line[5:].strip()
                        try:
                            chunk_data = json.loads(data_str)
                        except Exception:
                            continue

                        candidates = chunk_data.get("candidates", [])
                        if not candidates:
                            continue

                        cand = candidates[0]
                        parts = cand.get("content", {}).get("parts", [])
                        finish_reason = cand.get("finishReason")

                        for idx, p in enumerate(parts):
                            if "text" in p:
                                yield StreamChunk(delta_text=p["text"], finish_reason=finish_reason)
                            elif "functionCall" in p:
                                fc = p["functionCall"]
                                tc = ToolCall(
                                    id=f"call_{idx}_{fc.get('name')}",
                                    name=fc.get("name", ""),
                                    arguments=fc.get("args", {}),
                                )
                                yield StreamChunk(
                                    delta_tool_calls=[tc], finish_reason=finish_reason
                                )
            except httpx.HTTPStatusError as exc:
                self._handle_error(exc)
            except (httpx.ConnectError, httpx.TimeoutException) as exc:
                raise LLMProviderUnavailableError(
                    f"Gemini connection error: {exc}", provider="gemini", model=self.model
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
