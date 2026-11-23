"""Path sandboxing, directory jail enforcement, and symlink escape defense."""

import os
from pathlib import Path
from typing import IO, Any

from devpilot.core.exceptions import SafetyError


class PathSandbox:
    """Enforces strict path containment within the repository root directory."""

    def __init__(self, repo_root: str | Path) -> None:
        self.repo_root = Path(repo_root).resolve()

    def resolve_safe_path(self, relative_or_absolute_path: str | Path) -> Path:
        """Resolves target path and strictly validates it resides inside repo_root.

        Raises SafetyError on path traversal, absolute path escape, or symlink escape attempts.
        """
        raw_str = str(relative_or_absolute_path).strip()
        if not raw_str:
            raise SafetyError("Path cannot be empty", policy="path_sandbox")

        if "\x00" in raw_str:
            raise SafetyError(
                f"Path traversal detected: NUL byte in '{relative_or_absolute_path}'",
                policy="path_sandbox",
                details={"target": raw_str, "root": str(self.repo_root)},
            )

        # Explicitly reject backslash traversal attempts on all platforms
        if "\\" in raw_str and (".." in raw_str or raw_str.startswith("\\")):
            raise SafetyError(
                f"Path traversal detected: backslash traversal in '{relative_or_absolute_path}'",
                policy="path_sandbox",
                details={"target": raw_str, "root": str(self.repo_root)},
            )

        p = Path(raw_str)

        # Disallow explicit root / drive paths outside repo_root
        if p.is_absolute() or raw_str.startswith(("/", "\\")):
            try:
                resolved_abs = p.resolve()
                resolved_abs.relative_to(self.repo_root)
                self._verify_no_escaping_symlinks(resolved_abs)
                return resolved_abs
            except (ValueError, Exception) as exc:
                raise SafetyError(
                    f"Path traversal detected: absolute path '{relative_or_absolute_path}' escapes repository root '{self.repo_root}'",
                    policy="path_sandbox",
                    details={"target": str(p), "root": str(self.repo_root)},
                ) from exc

        target_path = (self.repo_root / raw_str).resolve()

        # Check for intermediate or dangling symlink escapes
        self._verify_no_escaping_symlinks(self.repo_root / raw_str)

        # Strict boundary check
        try:
            target_path.relative_to(self.repo_root)
        except ValueError as exc:
            raise SafetyError(
                f"Path traversal detected: '{relative_or_absolute_path}' escapes repository root '{self.repo_root}'",
                policy="path_sandbox",
                details={"target": str(target_path), "root": str(self.repo_root)},
            ) from exc

        return target_path

    def _verify_no_escaping_symlinks(self, path: Path) -> None:
        """Inspects all segments of path for escaping intermediate or dangling symlinks."""
        curr = self.repo_root
        try:
            rel_parts = path.resolve().relative_to(self.repo_root).parts
        except ValueError:
            # Already escapes root
            return

        for part in rel_parts:
            curr = curr / part
            if curr.is_symlink():
                # Check link target
                try:
                    link_dest = Path(os.readlink(curr))
                    if link_dest.is_absolute():
                        real_dest = link_dest.resolve()
                    else:
                        real_dest = (curr.parent / link_dest).resolve()
                    real_dest.relative_to(self.repo_root)
                except (ValueError, OSError) as exc:
                    raise SafetyError(
                        f"Symlink escape detected: link '{curr}' points outside sandbox to '{link_dest}'",
                        policy="path_sandbox",
                        details={"symlink": str(curr), "root": str(self.repo_root)},
                    ) from exc

    def safe_open(
        self,
        relative_or_absolute_path: str | Path,
        mode: str = "r",
        encoding: str | None = "utf-8",
        **kwargs: Any,
    ) -> IO[Any]:
        """Safely opens a file after verifying path containment and TOCTOU safety."""
        safe_path = self.resolve_safe_path(relative_or_absolute_path)

        # Ensure parent exists if opening for write
        if any(m in mode for m in ("w", "a", "+")):
            safe_path.parent.mkdir(parents=True, exist_ok=True)
            self.resolve_safe_path(safe_path.parent)

        if "b" in mode:
            return open(safe_path, mode=mode, **kwargs)
        return open(safe_path, mode=mode, encoding=encoding, **kwargs)

    def to_relative_path(self, path: str | Path) -> str:
        """Returns clean forward-slash relative path within repository root."""
        resolved = self.resolve_safe_path(path)
        rel = resolved.relative_to(self.repo_root)
        return str(rel).replace("\\", "/")
