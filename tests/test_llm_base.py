"""Unit tests for LLM base models and serialization."""

from devpilot.llm.base import (
    Message,
    Role,
    TokenUsage,
    ToolCall,
    ToolDefinition,
)


def test_tool_definition_conversions():
    tool = ToolDefinition(
        name="test_tool",
        description="A tool for testing",
        parameters={"type": "object", "properties": {"x": {"type": "integer"}}},
    )

    openai_schema = tool.to_openai_schema()
    assert openai_schema["type"] == "function"
    assert openai_schema["function"]["name"] == "test_tool"

    anthropic_schema = tool.to_anthropic_schema()
    assert anthropic_schema["name"] == "test_tool"
    assert "input_schema" in anthropic_schema

    gemini_schema = tool.to_gemini_schema()
    assert gemini_schema["name"] == "test_tool"
    assert "parameters" in gemini_schema


def test_tool_call_arguments_parsing():
    tc1 = ToolCall(id="call_1", name="read_file", arguments={"path": "main.py"})
    assert tc1.get_arguments_dict() == {"path": "main.py"}

    tc2 = ToolCall(id="call_2", name="read_file", raw_arguments='{"path": "test.py", "line": 10}')
    assert tc2.get_arguments_dict() == {"path": "test.py", "line": 10}


def test_message_helpers():
    m_sys = Message.system("System prompt")
    assert m_sys.role == Role.SYSTEM
    assert m_sys.content == "System prompt"

    m_user = Message.user("User prompt")
    assert m_user.role == Role.USER

    m_asst = Message.assistant(content="Answer")
    assert m_asst.role == Role.ASSISTANT

    m_tool = Message.tool_result(
        tool_call_id="call_1", content="File content here", name="read_file"
    )
    assert m_tool.role == Role.TOOL
    assert m_tool.tool_call_id == "call_1"


def test_token_usage_compute():
    usage = TokenUsage.compute(prompt=100, completion=50, cached=20)
    assert usage.prompt_tokens == 100
    assert usage.completion_tokens == 50
    assert usage.total_tokens == 150
    assert usage.cached_prompt_tokens == 20
