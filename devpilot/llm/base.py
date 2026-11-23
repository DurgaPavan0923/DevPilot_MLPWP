"""Abstract Base Class and unified data contracts for LLM providers."""

import json
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class Role(StrEnum):
    """Message roles for conversational LLM interactions."""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class ToolCall(BaseModel):
    """Standardized tool invocation payload returned by an LLM."""

    id: str = Field(..., description="Unique tool call identifier")
    name: str = Field(..., description="Target tool name")
    arguments: dict[str, Any] = Field(
        default_factory=dict, description="Parsed arguments dictionary"
    )
    raw_arguments: str | None = Field(None, description="Raw unparsed JSON string of arguments")

    def get_arguments_dict(self) -> dict[str, Any]:
        """Returns parsed arguments, falling back to parsing raw_arguments if empty."""
        if self.arguments:
            return self.arguments
        if self.raw_arguments:
            try:
                parsed = json.loads(self.raw_arguments)
                if isinstance(parsed, dict):
                    return parsed
            except Exception:
                return {}
        return {}


class ToolDefinition(BaseModel):
    """Specification of a tool exposed to the model for tool-calling."""

    name: str = Field(..., description="Identifier name of the tool")
    description: str = Field(..., description="Concise description of tool purpose and behavior")
    parameters: dict[str, Any] = Field(
        default_factory=lambda: {"type": "object", "properties": {}},
        description="JSON Schema defining acceptable parameter structure",
    )

    def to_openai_schema(self) -> dict[str, Any]:
        """Converts tool definition to OpenAI/DeepSeek function calling schema."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }

    def to_anthropic_schema(self) -> dict[str, Any]:
        """Converts tool definition to Anthropic tool schema."""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.parameters,
        }

    def to_gemini_schema(self) -> dict[str, Any]:
        """Converts tool definition to Gemini function declaration schema."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
        }


class Message(BaseModel):
    """Standardized chat message exchange item."""

    role: Role = Field(..., description="Role of message author")
    content: str | None = Field(None, description="Textual body content")
    name: str | None = Field(None, description="Optional name identifier for tool or user")
    tool_calls: list[ToolCall] | None = Field(
        None, description="Tool invocations requested by assistant"
    )
    tool_call_id: str | None = Field(
        None, description="Tool call ID this message responds to (for role=tool)"
    )

    @classmethod
    def system(cls, content: str) -> "Message":
        return cls(role=Role.SYSTEM, content=content)

    @classmethod
    def user(cls, content: str) -> "Message":
        return cls(role=Role.USER, content=content)

    @classmethod
    def assistant(
        cls, content: str | None = None, tool_calls: list[ToolCall] | None = None
    ) -> "Message":
        return cls(role=Role.ASSISTANT, content=content, tool_calls=tool_calls)

    @classmethod
    def tool_result(cls, tool_call_id: str, content: str, name: str | None = None) -> "Message":
        return cls(role=Role.TOOL, content=content, tool_call_id=tool_call_id, name=name)


class TokenUsage(BaseModel):
    """Token consumption statistics for an invocation."""

    prompt_tokens: int = Field(default=0, ge=0)
    completion_tokens: int = Field(default=0, ge=0)
    total_tokens: int = Field(default=0, ge=0)
    cached_prompt_tokens: int | None = Field(default=0, ge=0)

    @classmethod
    def compute(cls, prompt: int, completion: int, cached: int = 0) -> "TokenUsage":
        return cls(
            prompt_tokens=prompt,
            completion_tokens=completion,
            total_tokens=prompt + completion,
            cached_prompt_tokens=cached,
        )


class ChatResponse(BaseModel):
    """Unified response object returned by LLM chat completions."""

    message: Message = Field(..., description="Assistant output message")
    finish_reason: str | None = Field(
        None, description="Reason model stopped (stop, tool_calls, length, etc.)"
    )
    usage: TokenUsage = Field(default_factory=TokenUsage)
    cost_usd: float = Field(default=0.0, ge=0.0, description="Estimated monetary cost in USD")
    provider: str = Field(..., description="Provider identity string")
    model: str = Field(..., description="Model identity string")
    raw_response: dict[str, Any] | None = Field(None, description="Raw provider response payload")


class StreamChunk(BaseModel):
    """Incremental chunk emitted during streaming completions."""

    delta_text: str | None = Field(None, description="Incremental generated token text")
    delta_tool_calls: list[ToolCall] | None = Field(
        None, description="Incremental or assembled tool calls"
    )
    finish_reason: str | None = Field(None, description="Completion finish reason if terminated")
    usage: TokenUsage | None = Field(None, description="Final token usage if emitted in stream")


class LLMProvider(ABC):
    """Unified abstract interface across all LLM providers."""

    def __init__(self, model: str, api_key: str | None = None, **kwargs: Any) -> None:
        self.model = model
        self.api_key = api_key
        self.options = kwargs

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Returns the canonical provider name (e.g. openai, anthropic, gemini)."""
        pass

    @property
    def supports_native_tools(self) -> bool:
        """Indicates whether this provider natively formats and returns tool calls."""
        return True

    @abstractmethod
    async def chat(
        self,
        messages: list[Message],
        tools: list[ToolDefinition] | None = None,
        temperature: float = 0.0,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> ChatResponse:
        """Executes a standard asynchronous chat completion."""
        pass

    @abstractmethod
    def stream(
        self,
        messages: list[Message],
        tools: list[ToolDefinition] | None = None,
        temperature: float = 0.0,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[StreamChunk]:
        """Executes an asynchronous streaming chat completion yielding chunks."""
        pass

    @abstractmethod
    def count_tokens(self, text_or_messages: str | list[Message]) -> int:
        """Counts or estimates token length for the given text or message history."""
        pass

    def calculate_cost(self, usage: TokenUsage) -> float:
        """Calculates cost in USD for the given token usage."""
        from devpilot.llm.cost import calculate_cost as calc_cost

        return calc_cost(
            self.provider_name, self.model, usage.prompt_tokens, usage.completion_tokens
        )
