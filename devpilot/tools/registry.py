"""Tool registry holding active tool instances and dispatching invocations."""

from pathlib import Path
from typing import Any

from devpilot.core.types import ErrorTypeEnum, PermissionMode, ToolResult
from devpilot.llm.base import ToolDefinition
from devpilot.safety.command_policy import CommandPolicy
from devpilot.safety.permissions import PermissionManager
from devpilot.safety.sandbox import PathSandbox
from devpilot.tools.base import Tool
from devpilot.tools.create_file import CreateFileTool
from devpilot.tools.delete_file import DeleteFileTool
from devpilot.tools.edit_file import EditFileTool
from devpilot.tools.git_diff import GitDiffTool
from devpilot.tools.list_dir import ListDirTool
from devpilot.tools.read_file import ReadFileTool
from devpilot.tools.run_command import RunCommandTool
from devpilot.tools.run_tests import RunTestsTool
from devpilot.tools.search_code import SearchCodeTool


class ToolRegistry:
    """Manages active toolset, schema generation, and permission-gated execution."""

    def __init__(self, permission_manager: PermissionManager | None = None) -> None:
        self.tools: dict[str, Tool] = {}
        self.permission_manager = permission_manager or PermissionManager()

    def register(self, tool: Tool) -> None:
        """Registers a tool instance."""
        self.tools[tool.name] = tool

    def get_tool(self, name: str) -> Tool | None:
        """Retrieves a registered tool by name."""
        return self.tools.get(name)

    def get_definitions(self) -> list[ToolDefinition]:
        """Returns JSON schema definitions for all registered tools."""
        return [tool.to_tool_definition() for tool in self.tools.values()]

    async def execute(self, tool_name: str, arguments: dict[str, Any]) -> ToolResult:
        """Executes a tool with permission evaluation and uniform ToolResult envelope."""
        tool = self.get_tool(tool_name)
        if not tool:
            return ToolResult(
                ok=False,
                output=f"Tool '{tool_name}' is not recognized. Available tools: {', '.join(sorted(self.tools.keys()))}",
                error_type=ErrorTypeEnum.TOOL_MISUSE,
            )

        # Check safety permissions
        perm = self.permission_manager.check(tool_name, arguments)
        if not perm.allowed:
            return ToolResult(
                ok=False,
                output=f"Permission denied: {perm.reason}",
                error_type=ErrorTypeEnum.PERMISSION,
                metadata={"requires_approval": perm.requires_approval},
            )

        return await tool.run(**arguments)


def get_default_tool_registry(
    repo_root: Path,
    permission_mode: PermissionMode = PermissionMode.AUTO_SAFE,
    command_policy: CommandPolicy | None = None,
) -> ToolRegistry:
    """Constructs and returns standard tool registry initialized for a repository root."""
    sandbox = PathSandbox(repo_root)
    perm_mgr = PermissionManager(mode=permission_mode)
    registry = ToolRegistry(permission_manager=perm_mgr)

    registry.register(ReadFileTool(sandbox))
    registry.register(ListDirTool(sandbox))
    registry.register(SearchCodeTool(sandbox))
    registry.register(EditFileTool(sandbox))
    registry.register(CreateFileTool(sandbox))
    registry.register(DeleteFileTool(sandbox))
    registry.register(RunCommandTool(sandbox, policy=command_policy))
    registry.register(RunTestsTool(sandbox))
    registry.register(GitDiffTool(sandbox))

    return registry
