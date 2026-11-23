"""Tool: create_file."""

from typing import Any

from devpilot.core.types import ErrorTypeEnum, ToolResult
from devpilot.safety.sandbox import PathSandbox
from devpilot.tools.base import Tool


class CreateFileTool(Tool):
    name = "create_file"
    description = "Create a new file in the repository with the specified content. Automatically creates parent directories."
    parameters = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Relative file path to create"},
            "content": {"type": "string", "description": "Text content of the file"},
            "overwrite": {
                "type": "boolean",
                "description": "If False, fails if file already exists",
            },
        },
        "required": ["path", "content"],
    }

    def __init__(self, sandbox: PathSandbox) -> None:
        self.sandbox = sandbox

    async def execute(
        self, path: str = "", content: str = "", overwrite: bool = True, **kwargs: Any
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

        if target.exists() and not overwrite:
            return ToolResult(
                ok=False,
                output=f"File already exists: '{path}'. Pass overwrite=True to replace.",
                error_type=ErrorTypeEnum.TOOL_MISUSE,
            )

        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
            return ToolResult(
                ok=True,
                output=f"Successfully created file '{path}' ({len(content)} characters).",
                metadata={"file_path": path, "size_chars": len(content)},
            )
        except Exception as exc:
            return ToolResult(
                ok=False,
                output=f"Failed to create file '{path}': {str(exc)}",
                error_type=ErrorTypeEnum.ENVIRONMENT,
            )
