"""Tool: delete_file."""

from typing import Any

from devpilot.core.types import ErrorTypeEnum, ToolResult
from devpilot.safety.sandbox import PathSandbox
from devpilot.tools.base import Tool


class DeleteFileTool(Tool):
    name = "delete_file"
    description = "Delete a file from the repository."
    parameters = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Relative file path to delete"},
        },
        "required": ["path"],
    }

    def __init__(self, sandbox: PathSandbox) -> None:
        self.sandbox = sandbox

    async def execute(self, path: str = "", **kwargs: Any) -> ToolResult:
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
                ok=False,
                output=f"Cannot delete non-existent file: '{path}'",
                error_type=ErrorTypeEnum.TOOL_MISUSE,
            )

        if target.is_dir():
            return ToolResult(
                ok=False,
                output=f"Path is a directory, not a file: '{path}'",
                error_type=ErrorTypeEnum.TOOL_MISUSE,
            )

        try:
            target.unlink()
            return ToolResult(
                ok=True, output=f"Successfully deleted file '{path}'.", metadata={"file_path": path}
            )
        except Exception as exc:
            return ToolResult(
                ok=False,
                output=f"Failed to delete file '{path}': {str(exc)}",
                error_type=ErrorTypeEnum.ENVIRONMENT,
            )
