"""Fallback prompt injector and parser for models lacking native tool-calling."""

import json
import re
import uuid

from devpilot.core.logging import get_logger
from devpilot.llm.base import Message, Role, ToolCall, ToolDefinition

logger = get_logger("devpilot.llm.fallback")

TOOL_INSTRUCTION_TEMPLATE = """
### AVAILABLE TOOLS
You have access to the following tools to inspect, modify, and verify the repository:

{tools_description}

### TOOL INVOCATION FORMAT
When you need to call a tool, you MUST format your response using one of the following exact blocks:

```tool_call
{{
  "name": "tool_name",
  "arguments": {{
    "arg1": "value1"
  }}
}}
```
Alternatively:
<tool_call>
{{"name": "tool_name", "arguments": {{"arg1": "value1"}}}}
</tool_call>

You may include reasoning or explanation before or after the tool block.
If no tool is needed, respond with standard text.
"""


def inject_tool_instructions(
    messages: list[Message],
    tools: list[ToolDefinition],
) -> list[Message]:
    """Injects tool descriptions and invocation schemas into system instructions."""
    if not tools:
        return messages

    tools_desc_lines = []
    for tool in tools:
        tools_desc_lines.append(f"- **{tool.name}**: {tool.description}")
        tools_desc_lines.append(f"  Parameters schema: {json.dumps(tool.parameters, indent=2)}")

    tools_block = "\n".join(tools_desc_lines)
    instructions = TOOL_INSTRUCTION_TEMPLATE.format(tools_description=tools_block)

    augmented_messages: list[Message] = []
    found_system = False

    for msg in messages:
        if msg.role == Role.SYSTEM and not found_system:
            augmented_content = f"{msg.content or ''}\n\n{instructions}"
            augmented_messages.append(Message(role=Role.SYSTEM, content=augmented_content))
            found_system = True
        else:
            augmented_messages.append(msg)

    if not found_system:
        # Prepend new system message with instructions
        augmented_messages.insert(0, Message(role=Role.SYSTEM, content=instructions))

    return augmented_messages


def parse_fallback_tool_calls(content: str | None) -> tuple[str | None, list[ToolCall] | None]:
    """Extracts tool calls from completion text formatted via XML tags or code blocks."""
    if not content:
        return content, None

    tool_calls: list[ToolCall] = []
    cleaned_content = content

    # Pattern 1: <tool_call> ... </tool_call>
    xml_pattern = re.compile(r"<tool_call>([\s\S]*?)</tool_call>", re.IGNORECASE)
    for match in xml_pattern.finditer(content):
        raw_json = match.group(1).strip()
        parsed_call = _parse_json_tool(raw_json)
        if parsed_call:
            tool_calls.append(parsed_call)
    cleaned_content = xml_pattern.sub("", cleaned_content).strip()

    # Pattern 2: ```tool_call ... ``` or ```json ... ``` with "name" and "arguments"
    codeblock_pattern = re.compile(r"```(?:tool_call|json)?\s*([\s\S]*?)\s*```", re.IGNORECASE)
    for match in codeblock_pattern.finditer(content):
        raw_json = match.group(1).strip()
        parsed_call = _parse_json_tool(raw_json)
        if parsed_call and not any(
            tc.name == parsed_call.name and tc.arguments == parsed_call.arguments
            for tc in tool_calls
        ):
            tool_calls.append(parsed_call)
            # Strip out this block from text
            cleaned_content = cleaned_content.replace(match.group(0), "").strip()

    if not tool_calls:
        return content, None

    return (cleaned_content if cleaned_content else None), tool_calls


def _parse_json_tool(raw_json: str) -> ToolCall | None:
    """Helper to parse a JSON snippet into a ToolCall."""
    try:
        data = json.loads(raw_json)
        if not isinstance(data, dict):
            return None

        name = data.get("name") or data.get("tool")
        if not name or not isinstance(name, str):
            return None

        arguments = data.get("arguments") or data.get("args") or data.get("parameters") or {}
        if isinstance(arguments, str):
            try:
                arguments = json.loads(arguments)
            except Exception:
                arguments = {"raw": arguments}

        if not isinstance(arguments, dict):
            arguments = {}

        return ToolCall(
            id=f"call_{uuid.uuid4().hex[:10]}",
            name=name,
            arguments=arguments,
            raw_arguments=json.dumps(arguments),
        )
    except Exception as exc:
        logger.debug("fallback_tool_parse_failed", raw=raw_json[:100], error=str(exc))
        return None
