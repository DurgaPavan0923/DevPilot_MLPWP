"""Tool: git_diff."""

import asyncio
from typing import Any

from devpilot.core.types import ErrorTypeEnum, ToolResult
from devpilot.safety.sandbox import PathSandbox
from devpilot.tools.base import Tool


class GitDiffTool(Tool):
    name = "git_diff"
    description = "Inspect unstaged and staged changes in the repository relative to git HEAD."
    parameters = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Optional specific file or directory path"},
            "staged": {"type": "boolean", "description": "If True, view staged changes (--staged)"},
        },
    }

    def __init__(self, sandbox: PathSandbox) -> None:
        self.sandbox = sandbox

    async def execute(
        self, path: str | None = None, staged: bool = False, **kwargs: Any
    ) -> ToolResult:
        cmd_parts = ["git", "diff"]
        if staged:
            cmd_parts.append("--staged")
        if path:
            safe_target = self.sandbox.resolve_safe_path(path)
            cmd_parts.append(safe_target.relative_to(self.sandbox.repo_root).as_posix())

        cmd = " ".join(cmd_parts)
        try:
            process = await asyncio.create_subprocess_shell(
                cmd,
                cwd=str(self.sandbox.repo_root),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout_bytes, stderr_bytes = await asyncio.wait_for(process.communicate(), timeout=30.0)
            diff_text = stdout_bytes.decode("utf-8", errors="replace").strip()
            err_text = stderr_bytes.decode("utf-8", errors="replace").strip()

            if process.returncode != 0:
                return ToolResult(
                    ok=False,
                    output=f"Git diff error: {err_text}",
                    error_type=ErrorTypeEnum.ENVIRONMENT,
                    exit_code=process.returncode,
                )

            if not diff_text:
                return ToolResult(
                    ok=True,
                    output="(No modified files or differences detected relative to HEAD)",
                    metadata={"has_diff": False},
                )

            return ToolResult(
                ok=True, output=diff_text, metadata={"has_diff": True, "diff_len": len(diff_text)}
            )
        except Exception as exc:
            return ToolResult(
                ok=False,
                output=f"Failed to run git diff: {str(exc)}",
                error_type=ErrorTypeEnum.ENVIRONMENT,
            )
