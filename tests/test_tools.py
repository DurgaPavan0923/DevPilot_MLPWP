"""Unit tests for tool execution, edge cases, CRLF/LF normalization, and output truncation."""

from pathlib import Path

import pytest

from devpilot.core.types import ErrorTypeEnum
from devpilot.safety.sandbox import PathSandbox
from devpilot.tools.base import truncate_output
from devpilot.tools.create_file import CreateFileTool
from devpilot.tools.delete_file import DeleteFileTool
from devpilot.tools.edit_file import EditFileTool
from devpilot.tools.read_file import ReadFileTool
from devpilot.tools.run_command import RunCommandTool


@pytest.fixture
def sandbox_env(tmp_path: Path) -> PathSandbox:
    (tmp_path / "hello.txt").write_text("Line 1\nLine 2\nLine 3\nLine 4\n", encoding="utf-8")
    (tmp_path / "code.py").write_text(
        "def old_func():\n    return 1\n\ndef duplicate():\n    pass\n\ndef duplicate():\n    pass\n",
        encoding="utf-8",
    )
    return PathSandbox(tmp_path)


@pytest.mark.asyncio
async def test_read_file_tool_bounds(sandbox_env: PathSandbox):
    tool = ReadFileTool(sandbox_env)
    res = await tool.run(path="hello.txt", start_line=2, end_line=3)
    assert res.ok is True
    assert "Line 2" in res.output
    assert "Line 3" in res.output
    assert "Line 1" not in res.output


@pytest.mark.asyncio
async def test_edit_file_exact_match_success(sandbox_env: PathSandbox):
    tool = EditFileTool(sandbox_env)
    res = await tool.run(
        path="code.py",
        target="def old_func():\n    return 1",
        replacement="def new_func():\n    return 99",
    )
    assert res.ok is True
    content = (sandbox_env.repo_root / "code.py").read_text(encoding="utf-8")
    assert "def new_func():\n    return 99" in content


@pytest.mark.asyncio
async def test_edit_file_no_match_fails(sandbox_env: PathSandbox):
    tool = EditFileTool(sandbox_env)
    res = await tool.run(
        path="code.py",
        target="def non_existent_function():\n    pass",
        replacement="anything",
    )
    assert res.ok is False
    assert res.error_type == ErrorTypeEnum.TOOL_MISUSE
    assert "was not found" in res.output


@pytest.mark.asyncio
async def test_edit_file_ambiguous_non_unique_fails(sandbox_env: PathSandbox):
    tool = EditFileTool(sandbox_env)
    res = await tool.run(
        path="code.py",
        target="def duplicate():\n    pass",
        replacement="def unique():\n    pass",
    )
    assert res.ok is False
    assert res.error_type == ErrorTypeEnum.TOOL_MISUSE
    assert "appeared 2 times" in res.output


@pytest.mark.asyncio
async def test_edit_file_crlf_preservation(sandbox_env: PathSandbox):
    crlf_file = sandbox_env.repo_root / "crlf.py"
    crlf_file.write_bytes(b"first_line\r\nsecond_line\r\nthird_line\r\n")

    tool = EditFileTool(sandbox_env)
    res = await tool.run(
        path="crlf.py",
        target="second_line",
        replacement="replaced_line",
    )
    assert res.ok is True
    raw = crlf_file.read_bytes()
    assert b"\r\n" in raw
    assert b"replaced_line\r\n" in raw


@pytest.mark.asyncio
async def test_create_and_delete_file(sandbox_env: PathSandbox):
    create_tool = CreateFileTool(sandbox_env)
    del_tool = DeleteFileTool(sandbox_env)

    c_res = await create_tool.run(path="sub/new_file.py", content="x = 100\n")
    assert c_res.ok is True
    assert (sandbox_env.repo_root / "sub" / "new_file.py").exists()

    d_res = await del_tool.run(path="sub/new_file.py")
    assert d_res.ok is True
    assert not (sandbox_env.repo_root / "sub" / "new_file.py").exists()


@pytest.mark.asyncio
async def test_run_command_timeout(sandbox_env: PathSandbox):
    tool = RunCommandTool(sandbox_env, default_timeout_sec=0.2)
    res = await tool.run(command='python -c "import time; time.sleep(1.0)"')
    assert res.ok is False
    assert res.error_type == ErrorTypeEnum.TIMEOUT


def test_truncate_output_utility():
    huge_text = "A" * 100_000
    truncated, was_trunc = truncate_output(huge_text, max_chars=10_000)
    assert was_trunc is True
    assert len(truncated) < 15_000
    assert "truncated for context limit" in truncated
