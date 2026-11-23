"""Unit tests for repository analysis, AST parsing, and dependency graphs."""

from pathlib import Path

import pytest

from devpilot.repo.graph import RepoDependencyGraph
from devpilot.repo.index import RepoIndex
from devpilot.repo.parser import SymbolParser, SymbolType
from devpilot.repo.scanner import RepoScanner


@pytest.fixture
def sample_repo(tmp_path: Path) -> Path:
    """Creates a temporary synthetic repository with multi-language code and gitignore."""
    (tmp_path / ".gitignore").write_text("ignored_dir/\n*.tmp\n", encoding="utf-8")

    src = tmp_path / "src"
    src.mkdir()
    (src / "app.py").write_text(
        'import helper\n\nclass Server:\n    """Main server class."""\n    def start(self):\n        pass\n\ndef main():\n    pass\n',
        encoding="utf-8",
    )
    (src / "helper.py").write_text("def utility():\n    return 42\n", encoding="utf-8")

    ignored = tmp_path / "ignored_dir"
    ignored.mkdir()
    (ignored / "temp.py").write_text("x = 1\n", encoding="utf-8")

    return tmp_path


def test_scanner_respects_gitignore(sample_repo: Path):
    scanner = RepoScanner(sample_repo)
    result = scanner.scan()

    rel_paths = [f.rel_path for f in result.files]
    assert "src/app.py" in rel_paths
    assert "src/helper.py" in rel_paths
    assert not any("ignored_dir" in p for p in rel_paths)
    assert result.languages.get("python") == 2


def test_symbol_parser():
    code = """
class Calculator:
    \"\"\"Math calculator.\"\"\"
    def add(self, a, b):
        return a + b

def standalone_func():
    return True
"""
    symbols = SymbolParser.parse_file("calc.py", code, language="python")
    assert len(symbols) == 3

    cls_sym = next(s for s in symbols if s.symbol_type == SymbolType.CLASS)
    assert cls_sym.name == "Calculator"
    assert cls_sym.docstring == "Math calculator."

    method_sym = next(s for s in symbols if s.symbol_type == SymbolType.METHOD)
    assert method_sym.name == "add"
    assert method_sym.parent_name == "Calculator"

    fn_sym = next(s for s in symbols if s.symbol_type == SymbolType.FUNCTION)
    assert fn_sym.name == "standalone_func"


def test_dependency_graph_pagerank_and_neighbors():
    graph = RepoDependencyGraph()
    graph.add_edge("src/app.py", "src/helper.py", relationship="imports")
    graph.add_edge("src/helper.py", "src/utils.py", relationship="imports")

    deps = graph.get_dependencies("src/app.py")
    assert "src/helper.py" in deps

    dependents = graph.get_dependents("src/helper.py")
    assert "src/app.py" in dependents

    expanded = graph.expand_neighbors(["src/app.py"], max_hops=2)
    assert "src/helper.py" in expanded
    assert "src/utils.py" in expanded

    pr = graph.compute_pagerank()
    assert len(pr) == 3
    assert pr["src/helper.py"] > 0.0


def test_repo_index(sample_repo: Path):
    index = RepoIndex(sample_repo)
    index.build_full_index()

    assert index.scan_result is not None
    assert "src/app.py" in index.symbols_by_file
    symbols = index.symbols_by_file["src/app.py"]
    assert any(s.name == "Server" for s in symbols)
    assert len(index.summary) > 0
