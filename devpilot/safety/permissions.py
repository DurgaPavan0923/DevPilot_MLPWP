"""Permission evaluator governing tool authorizations based on safety modes."""

from typing import Any, NamedTuple

from devpilot.core.types import PermissionMode

READ_ONLY_TOOLS = {"read_file", "list_dir", "search_code", "git_diff"}
SAFE_WRITE_TOOLS = {"edit_file", "create_file", "delete_file"}
COMMAND_TOOLS = {"run_command", "run_tests"}


class PermissionCheckResult(NamedTuple):
    allowed: bool
    requires_approval: bool
    reason: str


class PermissionManager:
    """Evaluates whether a tool invocation is allowed, denied, or needs explicit approval."""

    def __init__(self, mode: PermissionMode = PermissionMode.AUTO_SAFE) -> None:
        self.mode = mode

    def check(self, tool_name: str, arguments: dict[str, Any]) -> PermissionCheckResult:
        """Determines execution permissions for a specific tool request."""
        # 1. READ_ONLY Mode: strictly forbid writes and shell commands
        if self.mode == PermissionMode.READ_ONLY:
            if tool_name in READ_ONLY_TOOLS:
                return PermissionCheckResult(
                    True, False, "Read operation permitted in read-only mode"
                )
            return PermissionCheckResult(
                False,
                False,
                f"Tool '{tool_name}' blocked: workspace is operating in read-only permission mode",
            )

        # 2. ASK Mode: read tools allowed; all writes & commands require approval
        if self.mode == PermissionMode.ASK:
            if tool_name in READ_ONLY_TOOLS:
                return PermissionCheckResult(True, False, "Read operation permitted")
            return PermissionCheckResult(
                False,
                True,
                f"Action '{tool_name}' requires explicit operator approval in 'ask' mode",
            )

        # 3. AUTO_SAFE Mode: reads & file edits auto-permitted; shell commands require approval
        if self.mode == PermissionMode.AUTO_SAFE:
            if tool_name in (READ_ONLY_TOOLS | SAFE_WRITE_TOOLS):
                return PermissionCheckResult(True, False, "Safe operation permitted")
            return PermissionCheckResult(
                False,
                True,
                f"Command execution '{tool_name}' requires approval in 'auto-safe' mode",
            )

        # 4. FULL Mode: all tools auto-approved
        return PermissionCheckResult(True, False, "Full access permitted")
