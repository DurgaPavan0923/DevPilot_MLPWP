"""Unit tests for fallback tool instruction injection and output parsing."""

from devpilot.llm.base import Message, ToolDefinition
from devpilot.llm.fallback import inject_tool_instructions, parse_fallback_tool_calls


def test_inject_tool_instructions():
    messages = [Message.user("Please list the directory contents.")]
    tools = [
        ToolDefinition(
            name="list_dir",
            description="List directory",
            parameters={"type": "object", "properties": {"path": {"type": "string"}}},
        )
    ]

    augmented = inject_tool_instructions(messages, tools)
    assert len(augmented) == 2
    assert augmented[0].role.value == "system"
    assert "list_dir" in augmented[0].content
    assert "AVAILABLE TOOLS" in augmented[0].content


def test_parse_fallback_tool_calls_xml():
    raw_response = """
    I will inspect the files first.
    <tool_call>
    {
        "name": "read_file",
        "arguments": {"path": "src/app.py", "start_line": 1, "end_line": 50}
    }
    </tool_call>
    Let me know once ready.
    """

    cleaned_text, tool_calls = parse_fallback_tool_calls(raw_response)
    assert tool_calls is not None
    assert len(tool_calls) == 1
    assert tool_calls[0].name == "read_file"
    assert tool_calls[0].arguments == {"path": "src/app.py", "start_line": 1, "end_line": 50}
    assert "<tool_call>" not in cleaned_text


def test_parse_fallback_tool_calls_markdown_codeblock():
    raw_response = """
    Executing command:
    ```tool_call
    {
        "name": "run_command",
        "arguments": {"command": "pytest tests/test_core.py"}
    }
    ```
    """

    cleaned_text, tool_calls = parse_fallback_tool_calls(raw_response)
    assert tool_calls is not None
    assert len(tool_calls) == 1
    assert tool_calls[0].name == "run_command"
    assert tool_calls[0].arguments == {"command": "pytest tests/test_core.py"}
