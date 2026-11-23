"""Extended tests for tools: search_code, list_dir, edit_file, git_diff, and run_tests."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from devpilot.core.types import ErrorTypeEnum
from devpilot.safety.sandbox import PathSandbox
from devpilot.tools.edit_file import EditFileTool
from devpilot.tools.git_diff import GitDiffTool
from devpilot.tools.list_dir import ListDirTool
from devpilot.tools.run_tests import RunTestsTool
from devpilot.tools.search_code import SearchCodeTool

# ============================================================================
# search_code Extended Tests
# ============================================================================


@pytest.mark.asyncio
async def test_search_code_nested_repo_regression(tmp_path: Path) -> None:
    """Regression test: search_code must work when repo is nested under .devpilot/build/workspace."""
    nested_root = tmp_path / ".devpilot" / "build" / "workspace"
    nested_root.mkdir(parents=True)
    (nested_root / "sample.py").write_text(
        "def unique_target_function():\n    return 42\n", encoding="utf-8"
    )
    (nested_root / "helper.py").write_text("# normal helper\n", encoding="utf-8")

    sandbox = PathSandbox(nested_root)
    tool = SearchCodeTool(sandbox)

    # Must find unique_target_function despite parent paths containing .devpilot and build
    res = await tool.run(query="unique_target_function")
    assert res.ok is True
    assert "sample.py" in res.output
    assert "unique_target_function" in res.output


@pytest.mark.asyncio
async def test_search_code_regex_and_limits(tmp_path: Path) -> None:
    (tmp_path / "data.txt").write_text(
        "item_100\nitem_200\nitem_300\nitem_400\nother_item\n", encoding="utf-8"
    )
    sandbox = PathSandbox(tmp_path)
    tool = SearchCodeTool(sandbox)

    # Regex search
    res = await tool.run(query=r"item_\d{3}", is_regex=True, max_matches=2)
    assert res.ok is True
    assert "item_100" in res.output
    assert "item_200" in res.output
    assert "item_300" not in res.output  # Capped at 2 matches

    # Missing query
    res_no_q = await tool.run(query="")
    assert res_no_q.ok is False
    assert res_no_q.error_type == ErrorTypeEnum.TOOL_MISUSE

    # Invalid regex
    res_bad_re = await tool.run(query="[unclosed_bracket", is_regex=True)
    assert res_bad_re.ok is False
    assert res_bad_re.error_type == ErrorTypeEnum.TOOL_MISUSE

    # Traversal path
    res_trav = await tool.run(query="test", path="../../outside")
    assert res_trav.ok is False
    assert res_trav.error_type == ErrorTypeEnum.PERMISSION


# ============================================================================
# list_dir Extended Tests
# ============================================================================


@pytest.mark.asyncio
async def test_list_dir_extended(tmp_path: Path) -> None:
    sandbox = PathSandbox(tmp_path)
    tool = ListDirTool(sandbox)

    # Create subdirectories and files
    (tmp_path / "subdir").mkdir()
    (tmp_path / "subdir" / "child.txt").write_text("content", encoding="utf-8")
    (tmp_path / "file1.txt").write_text("hello", encoding="utf-8")
    (tmp_path / "file2.txt").write_text("world", encoding="utf-8")

    # Normal list
    res = await tool.run(path=".")
    assert res.ok is True
    assert "[DIR]" in res.output
    assert "subdir" in res.output
    assert "[FILE] file1.txt" in res.output
    assert "[FILE] file2.txt" in res.output

    # Subdirectory list
    res_sub = await tool.run(path="subdir")
    assert res_sub.ok is True
    assert "child.txt" in res_sub.output

    # Max entries truncation
    res_trunc = await tool.run(path=".", max_entries=1)
    assert res_trunc.ok is True
    assert "Truncated" in res_trunc.output

    # Non-existent directory
    res_none = await tool.run(path="missing_dir")
    assert res_none.ok is False
    assert res_none.error_type == ErrorTypeEnum.TOOL_MISUSE

    # Path is not a directory
    res_not_dir = await tool.run(path="file1.txt")
    assert res_not_dir.ok is False
    assert res_not_dir.error_type == ErrorTypeEnum.TOOL_MISUSE

    # Traversal path
    res_trav = await tool.run(path="../outside")
    assert res_trav.ok is False
    assert res_trav.error_type == ErrorTypeEnum.PERMISSION


# ============================================================================
# edit_file Extended Tests
# ============================================================================


@pytest.mark.asyncio
async def test_edit_file_validation_and_errors(tmp_path: Path) -> None:
    sandbox = PathSandbox(tmp_path)
    tool = EditFileTool(sandbox)

    (tmp_path / "sub").mkdir()
    (tmp_path / "test.py").write_text("a = 1\na = 1\n", encoding="utf-8")

    # Missing path
    res = await tool.run(path="")
    assert res.ok is False
    assert res.error_type == ErrorTypeEnum.TOOL_MISUSE

    # Non-existent file
    res = await tool.run(path="missing.py", target="foo", replacement="bar")
    assert res.ok is False
    assert res.error_type == ErrorTypeEnum.TOOL_MISUSE

    # Directory instead of file
    res = await tool.run(path="sub", target="foo", replacement="bar")
    assert res.ok is False
    assert res.error_type == ErrorTypeEnum.TOOL_MISUSE

    # Traversal path
    res = await tool.run(path="../outside.py", target="foo", replacement="bar")
    assert res.ok is False
    assert res.error_type == ErrorTypeEnum.PERMISSION

    # Ambiguity (target appears multiple times)
    res = await tool.run(path="test.py", target="a = 1", replacement="a = 2")
    assert res.ok is False
    assert res.error_type == ErrorTypeEnum.TOOL_MISUSE
    assert "appeared 2 times" in res.output


@pytest.mark.asyncio
async def test_edit_file_crlf_and_unicode_preservation(tmp_path: Path) -> None:
    sandbox = PathSandbox(tmp_path)
    tool = EditFileTool(sandbox)

    # CRLF line endings
    crlf_file = tmp_path / "crlf.py"
    crlf_file.write_bytes(b"line1\r\nline2_target\r\nline3\r\n")

    res = await tool.run(path="crlf.py", target="line2_target", replacement="line2_replaced")
    assert res.ok is True
    new_bytes = crlf_file.read_bytes()
    assert b"\r\n" in new_bytes
    assert b"line2_replaced\r\n" in new_bytes

    # Unicode & emoji preservation
    uni_file = tmp_path / "unicode.py"
    uni_file.write_text("msg = 'Initial 🚀'\ncode = 'こんにちは'\n", encoding="utf-8")

    res_uni = await tool.run(
        path="unicode.py", target="msg = 'Initial 🚀'", replacement="msg = 'Updated ✨'"
    )
    assert res_uni.ok is True
    content = uni_file.read_text(encoding="utf-8")
    assert "Updated ✨" in content
    assert "こんにちは" in content


@pytest.mark.asyncio
async def test_edit_file_unified_diff(tmp_path: Path) -> None:
    sandbox = PathSandbox(tmp_path)
    tool = EditFileTool(sandbox)

    target_file = tmp_path / "diff_target.py"
    target_file.write_text("def foo():\n    return False\n", encoding="utf-8")

    # Valid unified diff
    valid_diff = """--- a/diff_target.py
+++ b/diff_target.py
@@ -1,2 +1,2 @@
 def foo():
-    return False
+    return True
"""
    res = await tool.run(path="diff_target.py", diff=valid_diff)
    assert res.ok is True
    assert "return True" in target_file.read_text(encoding="utf-8")

    # Mismatched unified diff
    bad_diff = """--- a/diff_target.py
+++ b/diff_target.py
@@ -1,2 +1,2 @@
 def foo():
-    return DOES_NOT_EXIST
+    return True
"""
    res_bad = await tool.run(path="diff_target.py", diff=bad_diff)
    assert res_bad.ok is False
    assert res_bad.error_type == ErrorTypeEnum.TOOL_MISUSE


# ============================================================================
# git_diff Extended Tests
# ============================================================================


@pytest.mark.asyncio
async def test_git_diff_spaces_injection_and_traversal(tmp_path: Path) -> None:
    sandbox = PathSandbox(tmp_path)
    tool = GitDiffTool(sandbox)

    # Initialize a real git repo in tmp_path
    init_p = await asyncio.create_subprocess_exec("git", "init", cwd=str(tmp_path))
    await init_p.communicate()
    # Configure user name/email for commit
    await (
        await asyncio.create_subprocess_exec(
            "git", "config", "user.name", "Tester", cwd=str(tmp_path)
        )
    ).communicate()
    await (
        await asyncio.create_subprocess_exec(
            "git", "config", "user.email", "test@test.com", cwd=str(tmp_path)
        )
    ).communicate()

    # Create file with a space in its name
    spaced_file = tmp_path / "file with spaces.py"
    spaced_file.write_text("orig = 1\n", encoding="utf-8")
    await (
        await asyncio.create_subprocess_exec("git", "add", "file with spaces.py", cwd=str(tmp_path))
    ).communicate()
    await (
        await asyncio.create_subprocess_exec("git", "commit", "-m", "init", cwd=str(tmp_path))
    ).communicate()

    # Modify spaced file
    spaced_file.write_text("orig = 999\n", encoding="utf-8")

    # Diff with space in path
    res_space = await tool.run(path="file with spaces.py")
    assert res_space.ok is True
    assert "orig = 999" in res_space.output

    # Shell injection attempt in path: "; touch marker"
    marker = tmp_path / "marker.txt"
    _ = await tool.run(path="file with spaces.py; touch marker.txt")
    # PathSandbox or git should safely handle or reject the argument; marker file must NOT exist
    assert not marker.exists()

    # Traversal path
    res_trav = await tool.run(path="../../outside")
    assert res_trav.ok is False
    assert res_trav.error_type == ErrorTypeEnum.PERMISSION


@pytest.mark.asyncio
async def test_git_diff_non_git_repo(tmp_path: Path) -> None:
    # A fresh directory without git init
    sandbox = PathSandbox(tmp_path)
    tool = GitDiffTool(sandbox)
    res = await tool.run()
    assert res.ok is False
    assert res.error_type == ErrorTypeEnum.ENVIRONMENT


# ============================================================================
# run_tests Extended Tests
# ============================================================================


def test_run_tests_command_detection(tmp_path: Path) -> None:
    sandbox = PathSandbox(tmp_path)
    tool = RunTestsTool(sandbox)

    # Pytest detection (default or pyproject.toml)
    (tmp_path / "pyproject.toml").write_text("[tool.pytest]", encoding="utf-8")
    cmd = tool._detect_test_command(test_target=None, framework=None)
    assert "-m pytest" in cmd

    # npm detection
    (tmp_path / "pyproject.toml").unlink()
    (tmp_path / "package.json").write_text("{}", encoding="utf-8")
    cmd_npm = tool._detect_test_command(test_target=None, framework=None)
    assert "npm test" in cmd_npm

    # Maven detection
    (tmp_path / "package.json").unlink()
    (tmp_path / "pom.xml").write_text("<project></project>", encoding="utf-8")
    cmd_mvn = tool._detect_test_command(test_target=None, framework=None)
    assert "mvn test" in cmd_mvn

    # Go detection
    (tmp_path / "pom.xml").unlink()
    (tmp_path / "go.mod").write_text("module test", encoding="utf-8")
    cmd_go = tool._detect_test_command(test_target=None, framework=None)
    assert "go test" in cmd_go

    # Framework override
    cmd_override = tool._detect_test_command(test_target="tests/foo.py", framework="pytest")
    assert "tests/foo.py" in cmd_override


@pytest.mark.asyncio
async def test_run_tests_real_pass_and_fail(tmp_path: Path) -> None:
    # Set up a real minimal pytest suite
    sandbox = PathSandbox(tmp_path)
    tool = RunTestsTool(sandbox)

    test_file = tmp_path / "test_sample.py"
    test_file.write_text(
        "def test_passing():\n    assert 1 == 1\n\ndef test_failing():\n    assert 1 == 2\n",
        encoding="utf-8",
    )

    # Test running passing test specifically
    res_pass = await tool.run(test_target="test_sample.py -k test_passing")
    assert res_pass.ok is True
    assert "1 passed" in res_pass.output

    # Test running failing test
    res_fail = await tool.run(test_target="test_sample.py -k test_failing")
    assert res_fail.ok is False
    assert res_fail.error_type == ErrorTypeEnum.TEST_FAILURE
    assert "1 failed" in res_fail.output
