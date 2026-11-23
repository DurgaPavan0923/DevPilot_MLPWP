"""Repository index manager supporting caching and incremental re-indexing."""

from pathlib import Path

from devpilot.core.logging import get_logger
from devpilot.repo.graph import RepoDependencyGraph
from devpilot.repo.parser import Symbol, SymbolParser, SymbolType
from devpilot.repo.scanner import RepoScanner, RepoScanResult
from devpilot.repo.summary import RepoSummaryGenerator

logger = get_logger("devpilot.repo.index")


class RepoIndex:
    """Central repository index holding scanned metadata, parsed symbols, and dependency graph."""

    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root.resolve()
        self.scan_result: RepoScanResult | None = None
        self.symbols_by_file: dict[str, list[Symbol]] = {}
        self.graph = RepoDependencyGraph()
        self.summary: str = ""

    def build_full_index(self) -> None:
        """Executes full repository scan, symbol parsing, and dependency graph construction."""
        logger.info("building_repo_index", repo=str(self.repo_root))
        scanner = RepoScanner(self.repo_root)
        self.scan_result = scanner.scan()

        self.symbols_by_file.clear()
        self.graph = RepoDependencyGraph()

        # Add all files as nodes
        for fmeta in self.scan_result.files:
            self.graph.add_node(fmeta.rel_path, node_type="file", metadata={"lang": fmeta.language})

            if fmeta.is_binary:
                continue

            # Parse symbols
            try:
                content = Path(fmeta.abs_path).read_text(encoding="utf-8", errors="ignore")
                symbols = SymbolParser.parse_file(fmeta.rel_path, content, fmeta.language)
                self.symbols_by_file[fmeta.rel_path] = symbols

                # Wire import dependencies
                for sym in symbols:
                    if sym.symbol_type == SymbolType.IMPORT:
                        # Attempt to resolve import to a local repo file
                        target_file = self._resolve_import_to_file(sym.name, fmeta.rel_path)
                        if target_file and target_file != fmeta.rel_path:
                            self.graph.add_edge(fmeta.rel_path, target_file, relationship="imports")
            except Exception as exc:
                logger.debug("symbol_parse_error", file=fmeta.rel_path, error=str(exc))

        self.summary = RepoSummaryGenerator.generate(self.scan_result)
        logger.info(
            "repo_index_built",
            total_files=self.scan_result.total_files,
            total_symbols=sum(len(s) for s in self.symbols_by_file.values()),
        )

    def incremental_update(self, changed_paths: list[str]) -> None:
        """Incrementally re-indexes only the modified or newly created files."""
        if not self.scan_result:
            self.build_full_index()
            return

        for rel_path in changed_paths:
            norm_path = rel_path.replace("\\", "/")
            abs_path = (self.repo_root / norm_path).resolve()

            if not abs_path.exists():
                # File deleted: remove from metadata and symbols
                self.scan_result.files = [
                    f for f in self.scan_result.files if f.rel_path != norm_path
                ]
                self.symbols_by_file.pop(norm_path, None)
                continue

            # Re-read and re-parse file
            try:
                content = abs_path.read_text(encoding="utf-8", errors="ignore")
                symbols = SymbolParser.parse_file(norm_path, content)
                self.symbols_by_file[norm_path] = symbols
            except Exception as exc:
                logger.debug("incremental_parse_error", file=norm_path, error=str(exc))

    def _resolve_import_to_file(self, import_target: str, current_file: str) -> str | None:
        """Resolves module/import string to a scanned relative file path."""
        if not self.scan_result:
            return None

        clean_target = import_target.replace(".", "/").strip("/")
        known_files = {f.rel_path for f in self.scan_result.files}

        candidates = [
            f"{clean_target}.py",
            f"{clean_target}/__init__.py",
            f"{clean_target}.js",
            f"{clean_target}.ts",
            f"{clean_target}/index.js",
            f"{clean_target}/index.ts",
        ]

        for cand in candidates:
            if cand in known_files:
                return cand

        # Check relative folder resolution
        curr_dir = str(Path(current_file).parent).replace("\\", "/")
        if curr_dir and curr_dir != ".":
            for cand in candidates:
                rel_cand = f"{curr_dir}/{cand}"
                if rel_cand in known_files:
                    return rel_cand

        return None

    def get_all_symbols(self) -> list[Symbol]:
        """Returns flat list of all parsed symbols in repository."""
        all_syms: list[Symbol] = []
        for sym_list in self.symbols_by_file.values():
            all_syms.extend(sym_list)
        return all_syms
