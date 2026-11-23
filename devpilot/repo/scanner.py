"""Git-aware repository scanner with language detection and manifest discovery."""

import fnmatch
import hashlib
import os
from pathlib import Path

from pydantic import BaseModel
from pydantic import Field as PydanticField

from devpilot.core.exceptions import RepositoryError
from devpilot.core.logging import get_logger

logger = get_logger("devpilot.repo.scanner")

DEFAULT_IGNORE_PATTERNS = [
    ".git",
    ".git/*",
    ".venv",
    ".venv/*",
    "venv",
    "venv/*",
    "node_modules",
    "node_modules/*",
    "__pycache__",
    "__pycache__/*",
    "*.pyc",
    "*.pyo",
    "*.pyd",
    ".pytest_cache",
    ".pytest_cache/*",
    ".ruff_cache",
    ".ruff_cache/*",
    ".mypy_cache",
    ".mypy_cache/*",
    "dist",
    "dist/*",
    "build",
    "build/*",
    "*.egg-info",
    "*.egg-info/*",
    ".DS_Store",
    "Thumbs.db",
    "*.lock",
    "*.min.js",
    "*.min.css",
]

LANGUAGE_EXTENSIONS: dict[str, str] = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".java": "java",
    ".go": "go",
    ".rs": "rust",
    ".c": "c",
    ".cpp": "cpp",
    ".h": "c",
    ".hpp": "cpp",
    ".rb": "ruby",
    ".php": "php",
    ".cs": "csharp",
    ".swift": "swift",
    ".kt": "kotlin",
    ".scala": "scala",
    ".sh": "bash",
    ".bash": "bash",
    ".sql": "sql",
    ".html": "html",
    ".css": "css",
    ".json": "json",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".toml": "toml",
    ".md": "markdown",
}

MANIFEST_FILES = {
    "pyproject.toml": "python",
    "setup.py": "python",
    "requirements.txt": "python",
    "Pipfile": "python",
    "package.json": "javascript/typescript",
    "pom.xml": "java",
    "build.gradle": "java",
    "build.gradle.kts": "kotlin",
    "go.mod": "go",
    "Cargo.toml": "rust",
    "Gemfile": "ruby",
}


class FileMetadata(BaseModel):
    """Metadata descriptor for a scanned repository file."""

    rel_path: str = PydanticField(..., description="Path relative to repository root")
    abs_path: str = PydanticField(..., description="Absolute filesystem path")
    size_bytes: int = PydanticField(..., ge=0)
    language: str | None = PydanticField(None)
    is_binary: bool = PydanticField(default=False)
    sha256: str = PydanticField(...)
    mtime: float = PydanticField(...)


class RepoScanResult(BaseModel):
    """Aggregated output from repository directory scanning."""

    repo_root: str
    files: list[FileMetadata] = PydanticField(default_factory=list)
    languages: dict[str, int] = PydanticField(default_factory=dict)
    manifests: list[str] = PydanticField(default_factory=list)
    entry_points: list[str] = PydanticField(default_factory=list)
    total_files: int = 0
    total_size_bytes: int = 0


class RepoScanner:
    """Scans repository file trees respecting .gitignore and filtering binary files."""

    def __init__(
        self,
        repo_root: Path,
        max_file_size_bytes: int = 1_000_000,
        custom_ignore_patterns: list[str] | None = None,
    ) -> None:
        self.repo_root = repo_root.resolve()
        if not self.repo_root.exists() or not self.repo_root.is_dir():
            raise RepositoryError(
                f"Repository path does not exist or is not a directory: {repo_root}",
                path=str(repo_root),
            )
        self.max_file_size = max_file_size_bytes
        self.ignore_patterns = list(DEFAULT_IGNORE_PATTERNS)
        if custom_ignore_patterns:
            self.ignore_patterns.extend(custom_ignore_patterns)
        self._load_gitignore()

    def _load_gitignore(self) -> None:
        gitignore_path = self.repo_root / ".gitignore"
        if gitignore_path.is_file():
            try:
                with open(gitignore_path, encoding="utf-8", errors="ignore") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#"):
                            clean_line = line.rstrip("/\\")
                            self.ignore_patterns.append(clean_line)
                            self.ignore_patterns.append(f"{clean_line}/*")
            except Exception as exc:
                logger.warning("failed_to_read_gitignore", error=str(exc))

    def is_ignored(self, rel_path: str) -> bool:
        norm_path = rel_path.replace("\\", "/").strip("/")
        parts = norm_path.split("/")

        for pattern in self.ignore_patterns:
            clean_pat = pattern.replace("\\", "/").strip("/")
            if fnmatch.fnmatch(norm_path, clean_pat) or fnmatch.fnmatch(
                norm_path, f"*/{clean_pat}"
            ):
                return True
            if norm_path.startswith(f"{clean_pat}/") or f"/{clean_pat}/" in f"/{norm_path}/":
                return True
            for part in parts:
                if fnmatch.fnmatch(part, clean_pat):
                    return True
        return False

    @staticmethod
    def is_binary_file(file_path: Path) -> bool:
        try:
            with open(file_path, "rb") as f:
                chunk = f.read(1024)
                if b"\x00" in chunk:
                    return True
            return False
        except Exception:
            return True

    def scan(self) -> RepoScanResult:
        files: list[FileMetadata] = []
        lang_counts: dict[str, int] = {}
        manifests: list[str] = []
        entry_points: list[str] = []
        total_size = 0

        for root, dirs, filenames in os.walk(self.repo_root):
            # In-place prune ignored directories for performance
            rel_dir = os.path.relpath(root, self.repo_root).replace("\\", "/")
            if rel_dir != "." and self.is_ignored(rel_dir):
                dirs.clear()
                continue

            dirs[:] = [
                d
                for d in dirs
                if not self.is_ignored(os.path.join(rel_dir, d) if rel_dir != "." else d)
            ]

            for fname in filenames:
                rel_fpath = (Path(rel_dir) / fname).as_posix() if rel_dir != "." else fname
                if self.is_ignored(rel_fpath):
                    continue

                abs_fpath = (self.repo_root / rel_fpath).resolve()
                try:
                    stat = abs_fpath.stat()
                    size = stat.st_size
                except OSError:
                    continue

                if size > self.max_file_size:
                    continue

                is_bin = self.is_binary_file(abs_fpath)
                ext = abs_fpath.suffix.lower()
                lang = LANGUAGE_EXTENSIONS.get(ext)

                try:
                    with open(abs_fpath, "rb") as f:
                        file_hash = hashlib.sha256(f.read()).hexdigest()
                except OSError:
                    file_hash = "unavailable"

                meta = FileMetadata(
                    rel_path=rel_fpath,
                    abs_path=str(abs_fpath),
                    size_bytes=size,
                    language=lang,
                    is_binary=is_bin,
                    sha256=file_hash,
                    mtime=stat.st_mtime,
                )
                files.append(meta)
                total_size += size

                if lang:
                    lang_counts[lang] = lang_counts.get(lang, 0) + 1

                if fname in MANIFEST_FILES:
                    manifests.append(rel_fpath)

                if fname in (
                    "main.py",
                    "app.py",
                    "index.js",
                    "index.ts",
                    "server.js",
                    "server.ts",
                    "Main.java",
                    "main.go",
                ):
                    entry_points.append(rel_fpath)

        return RepoScanResult(
            repo_root=str(self.repo_root),
            files=files,
            languages=lang_counts,
            manifests=manifests,
            entry_points=entry_points,
            total_files=len(files),
            total_size_bytes=total_size,
        )
