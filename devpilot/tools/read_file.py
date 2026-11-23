"""Tool: read_file."""

from typing import Any

from devpilot.core.types import ErrorTypeEnum, ToolResult
from devpilot.safety.sandbox import PathSandbox
from devpilot.tools.base import Tool


class ReadFileTool(Tool):
    name = "read_file"
    description = (
        "Read the contents of a text file from the repository, with optional line range bounds."
    )
    parameters = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Relative file path from repository root"},
            "start_line": {
                "type": "integer",
                "description": "1-based starting line number (inclusive)",
            },
            "end_line": {
                "type": "integer",
                "description": "1-based ending line number (inclusive)",
            },
        },
        "required": ["path"],
    }

    def __init__(self, sandbox: PathSandbox) -> None:
        self.sandbox = sandbox

    async def execute(
        self,
        path: str = "",
        start_line: int | None = None,
        end_line: int | None = None,
        **kwargs: Any,
    ) -> ToolResult:
        if not path:
            return ToolResult(
                ok=False,
                output="Missing required argument 'path'",
                error_type=ErrorTypeEnum.TOOL_MISUSE,
            )
        try:
            target = self.sandbox.resolve_safe_path(path)
        except Exception as exc:
            return ToolResult(ok=False, output=str(exc), error_type=ErrorTypeEnum.PERMISSION)

        if not target.exists():
            return ToolResult(
                ok=False, output=f"File not found: {path}", error_type=ErrorTypeEnum.TOOL_MISUSE
            )

        if target.is_dir():
            return ToolResult(
                ok=False,
                output=f"Path is a directory, not a file: {path}",
                error_type=ErrorTypeEnum.TOOL_MISUSE,
            )

        try:
            content = target.read_text(encoding="utf-8", errors="replace")
            lines = content.splitlines(keepends=True)
            total_lines = len(lines)

            s_line = max(1, start_line) if start_line is not None else 1
            e_line = min(total_lines, end_line) if end_line is not None else total_lines

            if s_line > total_lines:
                return ToolResult(
                    ok=True,
                    output=f"File '{path}' has {total_lines} lines; requested start_line {s_line} is out of bounds.",
                    metadata={"total_lines": total_lines},
                )

            selected_lines = lines[s_line - 1 : e_line]
            numbered_lines = [
                f"{idx + s_line:5d} | {line}" for idx, line in enumerate(selected_lines)
            ]
            output = "".join(numbered_lines)

            return ToolResult(
                ok=True,
                output=output,
                metadata={"total_lines": total_lines, "start_line": s_line, "end_line": e_line},
            )
        except Exception as exc:
            return ToolResult(
                ok=False,
                output=f"Error reading file '{path}': {str(exc)}",
                error_type=ErrorTypeEnum.ENVIRONMENT,
            )
