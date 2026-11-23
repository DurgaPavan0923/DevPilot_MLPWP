"""Tool: list_dir."""

from typing import Any

from devpilot.core.types import ErrorTypeEnum, ToolResult
from devpilot.safety.sandbox import PathSandbox
from devpilot.tools.base import Tool


class ListDirTool(Tool):
    name = "list_dir"
    description = "List files and subdirectories within a repository directory."
    parameters = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Relative directory path, defaults to repository root '.'",
            },
            "max_entries": {
                "type": "integer",
                "description": "Maximum entries to list, defaults to 100",
            },
        },
    }

    def __init__(self, sandbox: PathSandbox) -> None:
        self.sandbox = sandbox

    async def execute(self, path: str = ".", max_entries: int = 100, **kwargs: Any) -> ToolResult:
        try:
            target = self.sandbox.resolve_safe_path(path)
        except Exception as exc:
            return ToolResult(ok=False, output=str(exc), error_type=ErrorTypeEnum.PERMISSION)

        if not target.exists():
            return ToolResult(
                ok=False,
                output=f"Directory not found: {path}",
                error_type=ErrorTypeEnum.TOOL_MISUSE,
            )

        if not target.is_dir():
            return ToolResult(
                ok=False,
                output=f"Path is not a directory: {path}",
                error_type=ErrorTypeEnum.TOOL_MISUSE,
            )

        try:
            entries = []
            for item in sorted(target.iterdir()):
                if item.name.startswith(".git"):
                    continue
                type_marker = "[DIR] " if item.is_dir() else "[FILE]"
                size_str = f"({item.stat().st_size} bytes)" if item.is_file() else ""
                entries.append(f"{type_marker} {item.name} {size_str}".strip())

            truncated = False
            if len(entries) > max_entries:
                entries = entries[:max_entries]
                truncated = True
                entries.append(f"... [Truncated at {max_entries} entries] ...")

            output = f"Directory contents of '{path}':\n" + "\n".join(entries)
            return ToolResult(
                ok=True,
                output=output,
                truncated=truncated,
                metadata={"total_entries": len(entries)},
            )
        except Exception as exc:
            return ToolResult(
                ok=False,
                output=f"Error listing directory '{path}': {str(exc)}",
                error_type=ErrorTypeEnum.ENVIRONMENT,
            )
