"""Comprehensive HTTP mock transport tests for all LLM provider adapters.

Tests: OpenAI, DeepSeek, OpenAI-compatible, Anthropic, Gemini, and Ollama.
Covers:
- Chat text responses
- Tool calls (including malformed argument JSON)
- Usage & Cost accounting
- Streaming text, tool-call assembly, usage chunks, non-JSON lines
- HTTP error mappings (401, 429 + Retry-After, 400 context length, 5xx, other)
- Missing API keys
- Connection and timeout errors (chat and stream)
- Token counting
- Request payload shapes (tool schemas, system prompt placement, tool results)
"""

from __future__ import annotations

import json
from typing import Any

import httpx
import pytest

from devpilot.core.exceptions import (
    LLMAuthenticationError,
    LLMContextLengthExceededError,
    LLMError,
    LLMProviderUnavailableError,
    LLMRateLimitError,
)
from devpilot.llm.adapters.anthropic import AnthropicProvider
from devpilot.llm.adapters.deepseek import DeepSeekProvider
from devpilot.llm.adapters.gemini import GeminiProvider
from devpilot.llm.adapters.ollama import OllamaProvider
from devpilot.llm.adapters.openai import OpenAIProvider
from devpilot.llm.adapters.openai_compatible import OpenAICompatibleProvider
from devpilot.llm.base import Message, ToolCall, ToolDefinition


def patch_httpx_client(monkeypatch: pytest.MonkeyPatch, handler: Any) -> None:
    transport = httpx.MockTransport(handler)
    orig_client = httpx.AsyncClient

    def _client_factory(*args: Any, **kwargs: Any) -> httpx.AsyncClient:
        kwargs["transport"] = transport
        return orig_client(*args, **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", _client_factory)


@pytest.fixture
def sample_tool_def() -> ToolDefinition:
    return ToolDefinition(
        name="calculator",
        description="Calculate arithmetic expressions",
        parameters={
            "type": "object",
            "properties": {"expr": {"type": "string"}},
            "required": ["expr"],
        },
    )


# ============================================================================
# OpenAI Adapter Tests
# ============================================================================


@pytest.mark.asyncio
async def test_openai_chat_text_and_payload_shape(
    monkeypatch: pytest.MonkeyPatch, sample_tool_def: ToolDefinition
) -> None:
    captured_requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured_requests.append(request)
        body = {
            "id": "chatcmpl-123",
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": "Hello world!"},
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": 15,
                "completion_tokens": 8,
                "prompt_tokens_details": {"cached_tokens": 5},
            },
        }
        return httpx.Response(200, json=body)

    patch_httpx_client(monkeypatch, handler)

    provider = OpenAIProvider(model="gpt-4o", api_key="sk-test-key-123")
    messages = [
        Message.system("System instructions"),
        Message.user("Hello"),
        Message.assistant(
            "Prior response",
            tool_calls=[ToolCall(id="c1", name="calculator", arguments={"expr": "1+1"})],
        ),
        Message.tool_result("c1", "2", name="calculator"),
    ]

    resp = await provider.chat(messages, tools=[sample_tool_def], temperature=0.2, max_tokens=100)

    assert resp.message.content == "Hello world!"
    assert resp.finish_reason == "stop"
    assert resp.usage.prompt_tokens == 15
    assert resp.usage.completion_tokens == 8
    assert resp.usage.cached_prompt_tokens == 5
    assert resp.cost_usd > 0.0

    # Verify captured request payload
    assert len(captured_requests) == 1
    req = captured_requests[0]
    assert req.headers["Authorization"] == "Bearer sk-test-key-123"
    req_json = json.loads(req.content.decode("utf-8"))
    assert req_json["model"] == "gpt-4o"
    assert req_json["temperature"] == 0.2
    assert req_json["max_tokens"] == 100
    assert len(req_json["tools"]) == 1
    assert req_json["tools"][0]["function"]["name"] == "calculator"
    # Check tool result formatting in messages
    assert req_json["messages"][0]["role"] == "system"
    assert req_json["messages"][3]["role"] == "tool"
    assert req_json["messages"][3]["tool_call_id"] == "c1"


@pytest.mark.asyncio
async def test_openai_tool_calls_valid_and_malformed(monkeypatch: pytest.MonkeyPatch) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        body = {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [
                            {
                                "id": "call_1",
                                "type": "function",
                                "function": {
                                    "name": "read_file",
                                    "arguments": '{"path": "test.py"}',
                                },
                            },
                            {
                                "id": "call_2",
                                "type": "function",
                                "function": {
                                    "name": "broken_tool",
                                    "arguments": "NOT_VALID_JSON{}",
                                },
                            },
                        ],
                    },
                    "finish_reason": "tool_calls",
                }
            ],
            "usage": {"prompt_tokens": 10, "completion_tokens": 10},
        }
        return httpx.Response(200, json=body)

    patch_httpx_client(monkeypatch, handler)

    provider = OpenAIProvider(model="gpt-4o-mini", api_key="sk-test")
    resp = await provider.chat([Message.user("Run tools")])

    assert resp.finish_reason == "tool_calls"
    assert resp.message.tool_calls is not None
    assert len(resp.message.tool_calls) == 2
    assert resp.message.tool_calls[0].name == "read_file"
    assert resp.message.tool_calls[0].arguments == {"path": "test.py"}
    # Malformed arguments fall back to empty dict
    assert resp.message.tool_calls[1].name == "broken_tool"
    assert resp.message.tool_calls[1].arguments == {}
    assert resp.message.tool_calls[1].raw_arguments == "NOT_VALID_JSON{}"


@pytest.mark.asyncio
async def test_openai_streaming_and_non_json_lines(monkeypatch: pytest.MonkeyPatch) -> None:
    sse_lines = [
        ": keep-alive comment\n\n",
        "invalid non-json sse line\n\n",
        'data: {"choices":[{"delta":{"content":"Hel"},"finish_reason":null}]}\n\n',
        'data: {"choices":[{"delta":{"content":"lo"},"finish_reason":null}]}\n\n',
        'data: {"choices":[{"delta":{"tool_calls":[{"index":0,"id":"call_abc","function":{"name":"calc","arguments":"{\\"x\\": 1}"}}]},"finish_reason":null}]}\n\n',
        'data: {"choices":[{"delta":{},"finish_reason":"tool_calls"}],"usage":{"prompt_tokens":12,"completion_tokens":6}}\n\n',
        "data: [DONE]\n\n",
    ]
    sse_content = "".join(sse_lines).encode("utf-8")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, content=sse_content, headers={"Content-Type": "text/event-stream"}
        )

    patch_httpx_client(monkeypatch, handler)

    provider = OpenAIProvider(model="gpt-4o", api_key="sk-test")
    chunks = []
    async for chunk in provider.stream([Message.user("Hi")]):
        chunks.append(chunk)

    text_deltas = [c.delta_text for c in chunks if c.delta_text]
    assert "".join(text_deltas) == "Hello"
    tool_chunks = [c for c in chunks if c.delta_tool_calls]
    assert len(tool_chunks) == 1
    assert tool_chunks[0].delta_tool_calls[0].name == "calc"
    assert tool_chunks[0].delta_tool_calls[0].arguments == {"x": 1}
    usage_chunks = [c for c in chunks if c.usage is not None]
    assert len(usage_chunks) == 1
    assert usage_chunks[0].usage.total_tokens == 18


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("status_code", "err_body", "headers", "expected_exc"),
    [
        (401, {"error": {"message": "Invalid API key"}}, {}, LLMAuthenticationError),
        (
            429,
            {"error": {"message": "Rate limit exceeded"}},
            {"Retry-After": "2.5"},
            LLMRateLimitError,
        ),
        (400, {"error": {"message": "context_length_exceeded"}}, {}, LLMContextLengthExceededError),
        (503, {"error": {"message": "Server error"}}, {}, LLMProviderUnavailableError),
        (418, {"error": {"message": "I'm a teapot"}}, {}, LLMError),
    ],
)
async def test_openai_error_mappings(
    monkeypatch: pytest.MonkeyPatch,
    status_code: int,
    err_body: dict[str, Any],
    headers: dict[str, str],
    expected_exc: type[Exception],
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code, json=err_body, headers=headers)

    patch_httpx_client(monkeypatch, handler)

    provider = OpenAIProvider(model="gpt-4o", api_key="sk-test")
    with pytest.raises(expected_exc) as exc_info:
        await provider.chat([Message.user("Hello")])

    if status_code == 429:
        assert isinstance(exc_info.value, LLMRateLimitError)
        assert exc_info.value.retry_after == 2.5


@pytest.mark.asyncio
async def test_openai_missing_api_key() -> None:
    provider = OpenAIProvider(model="gpt-4o", api_key=None)
    with pytest.raises(LLMAuthenticationError):
        await provider.chat([Message.user("Hello")])


@pytest.mark.asyncio
async def test_openai_connect_and_timeout_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    def handler_timeout(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("Read timed out")

    patch_httpx_client(monkeypatch, handler_timeout)
    provider = OpenAIProvider(model="gpt-4o", api_key="sk-test")

    with pytest.raises(LLMProviderUnavailableError):
        await provider.chat([Message.user("Hello")])

    with pytest.raises(LLMProviderUnavailableError):
        async for _ in provider.stream([Message.user("Hello")]):
            pass


def test_openai_count_tokens() -> None:
    provider = OpenAIProvider(model="gpt-4o", api_key="sk-test")
    assert provider.count_tokens("Hello world from unit test") > 0
    msgs = [Message.system("system"), Message.user("user message"), Message.assistant("reply")]
    assert provider.count_tokens(msgs) > 10


# ============================================================================
# DeepSeek & OpenAI-Compatible Tests
# ============================================================================


@pytest.mark.asyncio
async def test_deepseek_adapter_properties_and_chat(monkeypatch: pytest.MonkeyPatch) -> None:
    captured_requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured_requests.append(request)
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {"role": "assistant", "content": "DeepSeek code"},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {"prompt_tokens": 20, "completion_tokens": 10},
            },
        )

    patch_httpx_client(monkeypatch, handler)

    provider = DeepSeekProvider(model="deepseek-coder", api_key="sk-ds-key")
    assert provider.provider_name == "deepseek"
    resp = await provider.chat([Message.user("Write a function")])
    assert resp.message.content == "DeepSeek code"
    assert captured_requests[0].url.host == "api.deepseek.com"


@pytest.mark.asyncio
async def test_openai_compatible_adapter(monkeypatch: pytest.MonkeyPatch) -> None:
    captured_requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured_requests.append(request)
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {"role": "assistant", "content": "vLLM output"},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {"prompt_tokens": 5, "completion_tokens": 5},
            },
        )

    patch_httpx_client(monkeypatch, handler)

    provider = OpenAICompatibleProvider(
        model="custom-model",
        api_key="sk-local",
        base_url="http://localhost:8080/v1",
        provider_name="vllm",
    )
    assert provider.provider_name == "vllm"
    resp = await provider.chat([Message.user("Hi")])
    assert resp.message.content == "vLLM output"
    assert captured_requests[0].url.port == 8080


# ============================================================================
# Anthropic Adapter Tests
# ============================================================================


@pytest.mark.asyncio
async def test_anthropic_chat_text_and_payload_shape(
    monkeypatch: pytest.MonkeyPatch, sample_tool_def: ToolDefinition
) -> None:
    captured_requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured_requests.append(request)
        body = {
            "id": "msg_123",
            "type": "message",
            "role": "assistant",
            "content": [
                {"type": "text", "text": "Claude response"},
                {"type": "tool_use", "id": "tu_1", "name": "calculator", "input": {"expr": "2+2"}},
            ],
            "stop_reason": "tool_use",
            "usage": {"input_tokens": 30, "output_tokens": 15},
        }
        return httpx.Response(200, json=body)

    patch_httpx_client(monkeypatch, handler)

    provider = AnthropicProvider(model="claude-3-5-sonnet-20241022", api_key="sk-ant-test-key")
    messages = [
        Message.system("Be helpful"),
        Message.user("Calculate 2+2"),
        Message.tool_result("tu_0", "4", name="calculator"),
    ]

    resp = await provider.chat(messages, tools=[sample_tool_def])

    assert resp.message.content == "Claude response"
    assert resp.finish_reason == "tool_use"
    assert resp.message.tool_calls is not None
    assert len(resp.message.tool_calls) == 1
    assert resp.message.tool_calls[0].name == "calculator"
    assert resp.message.tool_calls[0].arguments == {"expr": "2+2"}

    # Verify Anthropic payload shape: system prompt extracted to top-level key
    req_json = json.loads(captured_requests[0].content.decode("utf-8"))
    assert req_json["system"] == "Be helpful"
    assert captured_requests[0].headers["x-api-key"] == "sk-ant-test-key"
    assert req_json["tools"][0]["name"] == "calculator"
    assert req_json["tools"][0]["input_schema"]["type"] == "object"


@pytest.mark.asyncio
async def test_anthropic_streaming(monkeypatch: pytest.MonkeyPatch) -> None:
    sse_lines = [
        ": ping\n\n",
        'event: message_start\ndata: {"type":"message_start","message":{"usage":{"input_tokens":25}}}\n\n',
        'event: content_block_start\ndata: {"type":"content_block_start","index":0,"content_block":{"type":"tool_use","id":"tool_99","name":"calculator"}}\n\n',
        'event: content_block_delta\ndata: {"type":"content_block_delta","index":0,"delta":{"type":"input_json_delta","partial_json":"{\\"expr\\": "}}\n\n',
        'event: content_block_delta\ndata: {"type":"content_block_delta","index":0,"delta":{"type":"input_json_delta","partial_json":"\\"5*5\\"}"}}\n\n',
        'event: content_block_stop\ndata: {"type":"content_block_stop","index":0}\n\n',
        'event: content_block_delta\ndata: {"type":"content_block_delta","index":1,"delta":{"type":"text_delta","text":"Result is"}}\n\n',
        'event: message_delta\ndata: {"type":"message_delta","delta":{"stop_reason":"end_turn"},"usage":{"output_tokens":12}}\n\n',
    ]
    sse_content = "".join(sse_lines).encode("utf-8")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, content=sse_content, headers={"Content-Type": "text/event-stream"}
        )

    patch_httpx_client(monkeypatch, handler)

    provider = AnthropicProvider(model="claude-3-5-sonnet-20241022", api_key="sk-ant-test")
    chunks = []
    async for chunk in provider.stream([Message.user("Multiply")]):
        chunks.append(chunk)

    text_parts = [c.delta_text for c in chunks if c.delta_text]
    assert "Result is" in text_parts
    tool_parts = [c for c in chunks if c.delta_tool_calls]
    assert len(tool_parts) >= 1
    assert tool_parts[-1].delta_tool_calls[0].name == "calculator"
    assert tool_parts[-1].delta_tool_calls[0].arguments == {"expr": "5*5"}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("status_code", "err_body", "headers", "expected_exc"),
    [
        (401, {"error": {"message": "Invalid API Key"}}, {}, LLMAuthenticationError),
        (429, {"error": {"message": "Too Many Requests"}}, {"retry-after": "5"}, LLMRateLimitError),
        (529, {"error": {"message": "Overloaded"}}, {}, LLMRateLimitError),
        (400, {"error": {"message": "Prompt is too long"}}, {}, LLMContextLengthExceededError),
        (500, {"error": {"message": "Internal Error"}}, {}, LLMProviderUnavailableError),
        (403, {"error": {"message": "Forbidden"}}, {}, LLMError),
    ],
)
async def test_anthropic_error_mappings(
    monkeypatch: pytest.MonkeyPatch,
    status_code: int,
    err_body: dict[str, Any],
    headers: dict[str, str],
    expected_exc: type[Exception],
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code, json=err_body, headers=headers)

    patch_httpx_client(monkeypatch, handler)

    provider = AnthropicProvider(model="claude-3-5-sonnet-20241022", api_key="sk-ant-test")
    with pytest.raises(expected_exc):
        await provider.chat([Message.user("Hi")])


@pytest.mark.asyncio
async def test_anthropic_missing_key_and_timeouts(monkeypatch: pytest.MonkeyPatch) -> None:
    # Missing key
    provider_no_key = AnthropicProvider(api_key=None)
    with pytest.raises(LLMAuthenticationError):
        await provider_no_key.chat([Message.user("Hi")])

    # Connect error
    def handler_err(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("Connection refused")

    patch_httpx_client(monkeypatch, handler_err)
    provider = AnthropicProvider(api_key="sk-ant-test")
    with pytest.raises(LLMProviderUnavailableError):
        await provider.chat([Message.user("Hi")])


# ============================================================================
# Gemini Adapter Tests
# ============================================================================


@pytest.mark.asyncio
async def test_gemini_chat_text_and_tool_call(
    monkeypatch: pytest.MonkeyPatch, sample_tool_def: ToolDefinition
) -> None:
    captured_requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured_requests.append(request)
        body = {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {"text": "Gemini text"},
                            {"functionCall": {"name": "calculator", "args": {"expr": "9*9"}}},
                        ],
                        "role": "model",
                    },
                    "finishReason": "STOP",
                }
            ],
            "usageMetadata": {
                "promptTokenCount": 22,
                "candidatesTokenCount": 14,
                "cachedContentTokenCount": 0,
            },
        }
        return httpx.Response(200, json=body)

    patch_httpx_client(monkeypatch, handler)

    provider = GeminiProvider(model="gemini-1.5-pro", api_key="AIzaSyTestKey123")
    messages = [
        Message.system("Instruction"),
        Message.user("Compute 9*9"),
        Message.tool_result("call_1", "81", name="calculator"),
    ]

    resp = await provider.chat(messages, tools=[sample_tool_def])

    assert resp.message.content == "Gemini text"
    assert resp.finish_reason == "STOP"
    assert resp.message.tool_calls is not None
    assert len(resp.message.tool_calls) == 1
    assert resp.message.tool_calls[0].name == "calculator"
    assert resp.message.tool_calls[0].arguments == {"expr": "9*9"}

    # Verify Gemini payload shape
    req_json = json.loads(captured_requests[0].content.decode("utf-8"))
    assert "systemInstruction" in req_json
    assert "tools" in req_json
    assert req_json["tools"][0]["functionDeclarations"][0]["name"] == "calculator"
    assert captured_requests[0].headers["x-goog-api-key"] == "AIzaSyTestKey123"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("status_code", "err_body", "expected_exc"),
    [
        (
            400,
            {"error": {"message": "API key not valid. Please pass a valid API key."}},
            LLMAuthenticationError,
        ),
        (429, {"error": {"message": "Resource exhausted"}}, LLMRateLimitError),
        (503, {"error": {"message": "Service Unavailable"}}, LLMProviderUnavailableError),
        (403, {"error": {"message": "Permission denied"}}, LLMError),
    ],
)
async def test_gemini_error_mappings(
    monkeypatch: pytest.MonkeyPatch,
    status_code: int,
    err_body: dict[str, Any],
    expected_exc: type[Exception],
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code, json=err_body)

    patch_httpx_client(monkeypatch, handler)

    provider = GeminiProvider(model="gemini-1.5-pro", api_key="AIzaSyTestKey")
    with pytest.raises(expected_exc):
        await provider.chat([Message.user("Hello")])


@pytest.mark.asyncio
async def test_gemini_missing_key_and_timeouts(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = GeminiProvider(api_key=None)
    with pytest.raises(LLMAuthenticationError):
        await provider.chat([Message.user("Hello")])

    def handler_to(request: httpx.Request) -> httpx.Response:
        raise httpx.TimeoutException("Timeout")

    patch_httpx_client(monkeypatch, handler_to)
    provider_with_key = GeminiProvider(api_key="AIzaSyTestKey")
    with pytest.raises(LLMProviderUnavailableError):
        await provider_with_key.chat([Message.user("Hello")])


# ============================================================================
# Ollama Adapter Tests
# ============================================================================


@pytest.mark.asyncio
async def test_ollama_chat_and_fallback_tool_calling(
    monkeypatch: pytest.MonkeyPatch, sample_tool_def: ToolDefinition
) -> None:
    captured_requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured_requests.append(request)
        # Ollama returns tool call via JSON tag in text
        body = {
            "message": {
                "role": "assistant",
                "content": 'I will calculate it.\n<tool_call>{"name": "calculator", "arguments": {"expr": "100/4"}}</tool_call>',
            },
            "prompt_eval_count": 40,
            "eval_count": 25,
            "done": True,
        }
        return httpx.Response(200, json=body)

    patch_httpx_client(monkeypatch, handler)

    provider = OllamaProvider(model="deepseek-coder:6.7b", base_url="http://localhost:11434")
    assert provider.supports_native_tools is False

    resp = await provider.chat([Message.user("What is 100/4?")], tools=[sample_tool_def])

    assert resp.message.tool_calls is not None
    assert len(resp.message.tool_calls) == 1
    assert resp.message.tool_calls[0].name == "calculator"
    assert resp.message.tool_calls[0].arguments == {"expr": "100/4"}
    assert resp.usage.total_tokens == 65
    assert resp.cost_usd == 0.0  # Local Ollama costs 0


@pytest.mark.asyncio
async def test_ollama_streaming(monkeypatch: pytest.MonkeyPatch) -> None:
    ndjson_lines = [
        '{"message": {"content": "Thinking..."}}\n',
        "non-json line that should be skipped\n",
        '{"message": {"content": " done."},"done": true, "prompt_eval_count": 10, "eval_count": 5}\n',
    ]
    content = "".join(ndjson_lines).encode("utf-8")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=content)

    patch_httpx_client(monkeypatch, handler)

    provider = OllamaProvider(model="deepseek-coder:6.7b")
    chunks = []
    async for chunk in provider.stream([Message.user("Hello")]):
        chunks.append(chunk)

    text_parts = [c.delta_text for c in chunks if c.delta_text]
    assert "".join(text_parts) == "Thinking... done."


@pytest.mark.asyncio
async def test_ollama_server_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def handler_500(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="Internal Server Error")

    patch_httpx_client(monkeypatch, handler_500)
    provider = OllamaProvider(model="deepseek-coder:6.7b")
    with pytest.raises(LLMError):
        await provider.chat([Message.user("Hi")])


@pytest.mark.asyncio
async def test_ollama_connection_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def handler_conn_err(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("Ollama daemon down")

    patch_httpx_client(monkeypatch, handler_conn_err)
    provider = OllamaProvider(model="deepseek-coder:6.7b")
    with pytest.raises(LLMProviderUnavailableError):
        await provider.chat([Message.user("Hi")])
