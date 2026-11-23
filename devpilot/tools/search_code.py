"""Tool: search_code."""

import re
from typing import Any

from devpilot.core.types import ErrorTypeEnum, ToolResult
from devpilot.safety.sandbox import PathSandbox
from devpilot.tools.base import Tool


class SearchCodeTool(Tool):
    name = "search_code"
    description = "Search repository source code files for a literal substring or regex pattern."
    parameters = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search string or regular expression"},
            "path": {
                "type": "string",
                "description": "Optional directory or file scope to search within",
            },
            "is_regex": {"type": "boolean", "description": "True if query is a regular expression"},
            "max_matches": {"type": "integer", "description": "Maximum matching lines to return"},
        },
        "required": ["query"],
    }

    def __init__(self, sandbox: PathSandbox) -> None:
        self.sandbox = sandbox

    async def execute(
        self,
        query: str = "",
        path: str = ".",
        is_regex: bool = False,
        max_matches: int = 50,
        **kwargs: Any,
    ) -> ToolResult:
        if not query:
            return ToolResult(
                ok=False,
                output="Missing required argument 'query'",
                error_type=ErrorTypeEnum.TOOL_MISUSE,
            )
        try:
            target_dir = self.sandbox.resolve_safe_path(path)
        except Exception as exc:
            return ToolResult(ok=False, output=str(exc), error_type=ErrorTypeEnum.PERMISSION)

        try:
            pattern = re.compile(query if is_regex else re.escape(query), re.IGNORECASE)
        except re.error as exc:
            return ToolResult(
                ok=False,
                output=f"Invalid search regex pattern: {str(exc)}",
                error_type=ErrorTypeEnum.TOOL_MISUSE,
            )

        matches: list[str] = []
        files_searched = 0

        search_files = [target_dir] if target_dir.is_file() else target_dir.rglob("*")

        for fpath in search_files:
            if not fpath.is_file():
                continue
            if any(
                part.startswith((".", "__pycache__", "node_modules", "dist", "build"))
                for part in fpath.parts
            ):
                continue

            files_searched += 1
            rel_path = fpath.relative_to(self.sandbox.repo_root).as_posix()

            try:
                content = fpath.read_text(encoding="utf-8", errors="ignore")
                for line_no, line in enumerate(content.splitlines(), start=1):
                    if pattern.search(line):
                        matches.append(f"{rel_path}:{line_no}: {line.strip()[:150]}")
                        if len(matches) >= max_matches:
                            break
            except Exception:
                continue

            if len(matches) >= max_matches:
                break

        if not matches:
            return ToolResult(
                ok=True,
                output=f"No matches found for '{query}' across {files_searched} files.",
                metadata={"matches": 0, "files_searched": files_searched},
            )

        output = f"Found {len(matches)} matches:\n" + "\n".join(matches)
        return ToolResult(
            ok=True,
            output=output,
            metadata={"matches": len(matches), "files_searched": files_searched},
        )
