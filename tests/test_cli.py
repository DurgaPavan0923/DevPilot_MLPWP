"""Unit tests for DevPilot CLI commands using Typer's CliRunner."""

from pathlib import Path

from typer.testing import CliRunner

from devpilot import __version__
from devpilot.cli import app

runner = CliRunner()


def test_cli_version():
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert __version__ in result.stdout


def test_cli_run_mock_task(tmp_path: Path):
    (tmp_path / "hello.py").write_text("print('hello')", encoding="utf-8")
    result = runner.invoke(
        app,
        [
            "run",
            "Say hello",
            "--repo",
            str(tmp_path),
            "--config",
            "full",
            "--provider",
            "mock",
            "--permission",
            "auto-safe",
        ],
    )
    assert result.exit_code == 0
    assert "Run Finished:" in result.stdout
    assert "COMPLETED" in result.stdout or "UNVERIFIED" in result.stdout


def test_cli_index_command(tmp_path: Path):
    (tmp_path / "mod.py").write_text("def add(a, b): return a + b\n", encoding="utf-8")
    result = runner.invoke(app, ["index", "--repo", str(tmp_path)])
    assert result.exit_code == 0
    assert "Index Complete:" in result.stdout
    assert "Total Files:" in result.stdout


def test_cli_sessions_list():
    result = runner.invoke(app, ["sessions", "--limit", "5"])
    assert result.exit_code == 0


def test_cli_eval_builtin_sample(tmp_path: Path):
    out_dir = tmp_path / "eval_out"
    result = runner.invoke(
        app,
        [
            "eval",
            "--configs",
            "basic",
            "--seeds",
            "42",
            "--concurrency",
            "1",
            "--output",
            str(out_dir),
        ],
    )
    assert result.exit_code == 0
    assert "Benchmark Completed:" in result.stdout
    assert (out_dir / "latest_evaluation_report.json").exists()
