"""Tool: edit_file with strict uniqueness checking, CRLF/LF normalization, and unified diff support."""

from pathlib import Path
from typing import Any

from devpilot.core.types import ErrorTypeEnum, ToolResult
from devpilot.safety.sandbox import PathSandbox
from devpilot.tools.base import Tool


class EditFileTool(Tool):
    name = "edit_file"
    description = (
        "Modify an existing file using either exact string search-and-replace (with mandatory uniqueness) "
        "or a unified diff patch. Replaces exactly one unique target occurrence."
    )
    parameters = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Relative file path to modify"},
            "target": {
                "type": "string",
                "description": "Exact text block to replace (must match uniquely)",
            },
            "replacement": {"type": "string", "description": "New replacement text"},
            "diff": {"type": "string", "description": "Optional unified diff patch string"},
        },
        "required": ["path"],
    }

    def __init__(self, sandbox: PathSandbox) -> None:
        self.sandbox = sandbox

    async def execute(
        self,
        path: str = "",
        target: str | None = None,
        replacement: str | None = None,
        diff: str | None = None,
        **kwargs: Any,
    ) -> ToolResult:
        if not path:
            return ToolResult(
                ok=False,
                output="Missing required argument 'path'",
                error_type=ErrorTypeEnum.TOOL_MISUSE,
            )
        try:
            target_path = self.sandbox.resolve_safe_path(path)
        except Exception as exc:
            return ToolResult(ok=False, output=str(exc), error_type=ErrorTypeEnum.PERMISSION)

        if not target_path.exists():
            return ToolResult(
                ok=False,
                output=f"Cannot edit non-existent file: {path}",
                error_type=ErrorTypeEnum.TOOL_MISUSE,
            )

        if target_path.is_dir():
            return ToolResult(
                ok=False,
                output=f"Path is a directory, not a file: {path}",
                error_type=ErrorTypeEnum.TOOL_MISUSE,
            )

        try:
            raw_bytes = target_path.read_bytes()
            # Detect original line ending format
            has_crlf = b"\r\n" in raw_bytes
            original_content = raw_bytes.decode("utf-8", errors="replace")
        except Exception as exc:
            return ToolResult(
                ok=False,
                output=f"Error reading file '{path}': {str(exc)}",
                error_type=ErrorTypeEnum.ENVIRONMENT,
            )

        # Mode A: Search and Replace
        if target is not None:
            if replacement is None:
                return ToolResult(
                    ok=False,
                    output="Must provide 'replacement' when 'target' is specified.",
                    error_type=ErrorTypeEnum.TOOL_MISUSE,
                )

            # Normalize line endings for comparison
            norm_content = original_content.replace("\r\n", "\n")
            norm_target = target.replace("\r\n", "\n")
            norm_replacement = replacement.replace("\r\n", "\n")

            occurrences = norm_content.count(norm_target)
            if occurrences == 0:
                # Provide helpful diagnostic context
                first_target_line = (
                    norm_target.splitlines()[0] if norm_target.splitlines() else norm_target
                )
                return ToolResult(
                    ok=False,
                    output=(
                        f"Edit failed: target block was not found in '{path}'.\n"
                        f"First line searched: '{first_target_line[:80]}'.\n"
                        "Please use read_file to inspect the exact lines and include exact leading whitespace."
                    ),
                    error_type=ErrorTypeEnum.TOOL_MISUSE,
                    metadata={"occurrences": 0},
                )

            if occurrences > 1:
                return ToolResult(
                    ok=False,
                    output=(
                        f"Edit failed: target block is ambiguous and appeared {occurrences} times in '{path}'.\n"
                        "Please include more surrounding context lines in 'target' to make the match unique."
                    ),
                    error_type=ErrorTypeEnum.TOOL_MISUSE,
                    metadata={"occurrences": occurrences},
                )

            # Exactly one match: perform replacement
            new_content = norm_content.replace(norm_target, norm_replacement, 1)

            # Restore original line endings
            if has_crlf:
                new_content = new_content.replace("\n", "\r\n")

            target_path.write_bytes(new_content.encode("utf-8"))
            return ToolResult(
                ok=True,
                output=f"Successfully edited '{path}'. Replaced 1 unique target occurrence.",
                metadata={"file_path": path, "occurrences": 1},
            )

        # Mode B: Unified Diff Patch
        if diff:
            return self._apply_unified_diff(target_path, original_content, diff, path, has_crlf)

        return ToolResult(
            ok=False,
            output="Must provide either ('target' and 'replacement') or 'diff' parameter.",
            error_type=ErrorTypeEnum.TOOL_MISUSE,
        )

    def _apply_unified_diff(
        self,
        file_path: Path,
        content: str,
        patch: str,
        rel_path: str,
        has_crlf: bool,
    ) -> ToolResult:
        """Applies unified diff patch hunk by hunk."""
        lines = content.replace("\r\n", "\n").splitlines()
        patch_lines = patch.replace("\r\n", "\n").splitlines()

        # Simple robust hunk applier
        hunk_lines = [
            line for line in patch_lines if not line.startswith(("---", "+++", "diff", "index"))
        ]
        removals = [line[1:] for line in hunk_lines if line.startswith("-")]
        additions = [line[1:] for line in hunk_lines if line.startswith("+")]

        if removals:
            target_sub = "\n".join(removals)
            replace_sub = "\n".join(additions)
            joined = "\n".join(lines)
            if target_sub in joined:
                joined = joined.replace(target_sub, replace_sub, 1)
                if has_crlf:
                    joined = joined.replace("\n", "\r\n")
                file_path.write_bytes(joined.encode("utf-8"))
                return ToolResult(
                    ok=True, output=f"Successfully applied diff patch to '{rel_path}'."
                )

        return ToolResult(
            ok=False,
            output=f"Failed to apply unified diff to '{rel_path}': patch hunks did not match file content cleanly.",
            error_type=ErrorTypeEnum.TOOL_MISUSE,
        )
