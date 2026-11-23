"""Targeted tests for verification runner, framework detector, tools edge cases, and LLM factory."""

from __future__ import annotations

from pathlib import Path

import pytest

from devpilot.core.exceptions import LLMError
from devpilot.core.types import ErrorTypeEnum
from devpilot.llm.factory import create_provider, get_default_provider
from devpilot.safety.sandbox import PathSandbox
from devpilot.tools.create_file import CreateFileTool
from devpilot.tools.delete_file import DeleteFileTool
from devpilot.tools.read_file import ReadFileTool
from devpilot.verify.detector import TestFramework, TestFrameworkDetector
from devpilot.verify.runner import VerificationRunner

# ============================================================================
# Test Framework Detector Tests
# ============================================================================


def test_framework_detector_all_types(tmp_path: Path) -> None:
    # Unknown initially
    assert TestFrameworkDetector.detect(tmp_path) == TestFramework.UNKNOWN

    # Pytest via pytest.ini
    pytest_ini = tmp_path / "pytest.ini"
    pytest_ini.write_text("[pytest]", encoding="utf-8")
    assert TestFrameworkDetector.detect(tmp_path) == TestFramework.PYTEST
    pytest_ini.unlink()

    # Pytest via tests folder
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    assert TestFrameworkDetector.detect(tmp_path) == TestFramework.PYTEST
    tests_dir.rmdir()

    # Jest via package.json
    pkg_json = tmp_path / "package.json"
    pkg_json.write_text('{"devDependencies": {"jest": "^29.0"}}', encoding="utf-8")
    assert TestFrameworkDetector.detect(tmp_path) == TestFramework.JEST

    # Mocha via package.json
    pkg_json.write_text('{"devDependencies": {"mocha": "^10.0"}}', encoding="utf-8")
    assert TestFrameworkDetector.detect(tmp_path) == TestFramework.MOCHA
    pkg_json.unlink()

    # Maven via pom.xml
    pom = tmp_path / "pom.xml"
    pom.write_text("<project></project>", encoding="utf-8")
    assert TestFrameworkDetector.detect(tmp_path) == TestFramework.MAVEN
    pom.unlink()

    # Gradle via build.gradle
    gradle = tmp_path / "build.gradle"
    gradle.write_text("// gradle", encoding="utf-8")
    assert TestFrameworkDetector.detect(tmp_path) == TestFramework.GRADLE
    gradle.unlink()

    # Gradle via build.gradle.kts
    gradle_kts = tmp_path / "build.gradle.kts"
    gradle_kts.write_text("// gradle kts", encoding="utf-8")
    assert TestFrameworkDetector.detect(tmp_path) == TestFramework.GRADLE
    gradle_kts.unlink()

    # Go test via go.mod
    go_mod = tmp_path / "go.mod"
    go_mod.write_text("module example.com/test", encoding="utf-8")
    assert TestFrameworkDetector.detect(tmp_path) == TestFramework.GO_TEST
    go_mod.unlink()


# ============================================================================
# Verification Runner Tests
# ============================================================================


def test_verification_runner_argv_generation(tmp_path: Path) -> None:
    runner = VerificationRunner(tmp_path)

    runner.framework = TestFramework.PYTEST
    argv = runner._get_test_argv("test_target.py")
    assert "pytest" in argv[2]
    assert argv[-1] == "test_target.py"

    runner.framework = TestFramework.JEST
    argv = runner._get_test_argv("test.js")
    assert argv[:3] == ["npm", "test", "--"]
    assert argv[-1] == "test.js"

    runner.framework = TestFramework.MAVEN
    assert runner._get_test_argv() == ["mvn", "test"]

    runner.framework = TestFramework.GRADLE
    argv_gradle = runner._get_test_argv()
    assert "gradlew" in argv_gradle[0]
    assert argv_gradle[1] == "test"

    runner.framework = TestFramework.GO_TEST
    argv_go = runner._get_test_argv("pkg/...")
    assert argv_go == ["go", "test", "pkg/..."]

    runner.framework = TestFramework.UNITTEST
    argv_unit = runner._get_test_argv("tests.py")
    assert "unittest" in argv_unit[2]
    assert argv_unit[-1] == "tests.py"

    runner.framework = TestFramework.UNKNOWN
    assert runner._get_test_argv() == []


@pytest.mark.asyncio
async def test_verification_runner_execution(tmp_path: Path) -> None:
    # 1. Unknown framework
    runner_unknown = VerificationRunner(tmp_path)
    res_unknown = await runner_unknown.run_verification()
    assert res_unknown.status == "UNVERIFIED"
    assert res_unknown.passed is False

    # 2. Pytest framework - passing test
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    test_py = tests_dir / "test_ok.py"
    test_py.write_text("def test_ok():\n    assert True\n", encoding="utf-8")

    runner_pytest = VerificationRunner(tmp_path)
    assert runner_pytest.framework == TestFramework.PYTEST

    report = await runner_pytest.run_verification(target_test="tests/test_ok.py")
    assert report.status == "VERIFIED"
    assert report.passed is True

    # 3. Failing test
    test_fail = tests_dir / "test_bad.py"
    test_fail.write_text("def test_fail():\n    assert False\n", encoding="utf-8")
    report_fail = await runner_pytest.run_verification(target_test="tests/test_bad.py")
    assert report_fail.status == "FAILED"
    assert report_fail.passed is False


# ============================================================================
# Extended Tool Edge Cases Tests
# ============================================================================


@pytest.mark.asyncio
async def test_read_file_edge_cases(tmp_path: Path) -> None:
    sandbox = PathSandbox(tmp_path)
    tool = ReadFileTool(sandbox)

    # Missing path
    res_no_path = await tool.run(path="")
    assert res_no_path.ok is False
    assert res_no_path.error_type == ErrorTypeEnum.TOOL_MISUSE

    # Non-existent file
    res_missing = await tool.run(path="does_not_exist.txt")
    assert res_missing.ok is False
    assert res_missing.error_type == ErrorTypeEnum.TOOL_MISUSE
    assert "File not found" in res_missing.output

    # Path is directory
    sub_dir = tmp_path / "my_dir"
    sub_dir.mkdir()
    res_dir = await tool.run(path="my_dir")
    assert res_dir.ok is False
    assert "directory" in res_dir.output

    # Path traversal attack
    res_traversal = await tool.run(path="../outside.txt")
    assert res_traversal.ok is False
    assert res_traversal.error_type == ErrorTypeEnum.PERMISSION

    # Out of bounds start line
    text_file = tmp_path / "lines.txt"
    text_file.write_text("\n".join(f"line_{i}" for i in range(1, 20)), encoding="utf-8")
    res_oob = await tool.run(path="lines.txt", start_line=500)
    assert res_oob.ok is True
    assert "out of bounds" in res_oob.output

    # Large line count / start and end lines
    res_lines = await tool.run(path="lines.txt", start_line=5, end_line=7)
    assert res_lines.ok is True
    assert "line_5" in res_lines.output
    assert "line_7" in res_lines.output
    assert "line_4" not in res_lines.output
    assert "line_8" not in res_lines.output


@pytest.mark.asyncio
async def test_create_file_edge_cases(tmp_path: Path) -> None:
    sandbox = PathSandbox(tmp_path)
    tool = CreateFileTool(sandbox)

    # Missing path
    res_no_path = await tool.run(path="", content="hello")
    assert res_no_path.ok is False
    assert res_no_path.error_type == ErrorTypeEnum.TOOL_MISUSE

    # Path traversal
    res_traversal = await tool.run(path="../../secret.txt", content="secret")
    assert res_traversal.ok is False
    assert res_traversal.error_type == ErrorTypeEnum.PERMISSION

    # Existing file with overwrite=False
    existing = tmp_path / "exist.txt"
    existing.write_text("original content", encoding="utf-8")
    res_exist = await tool.run(path="exist.txt", content="new content", overwrite=False)
    assert res_exist.ok is False
    assert "already exists" in res_exist.output

    # Existing file with overwrite=True
    res_overwrite = await tool.run(path="exist.txt", content="new content", overwrite=True)
    assert res_overwrite.ok is True
    assert existing.read_text(encoding="utf-8") == "new content"

    # Directory collision
    folder = tmp_path / "a_dir"
    folder.mkdir()
    res_coll = await tool.run(path="a_dir", content="test")
    assert res_coll.ok is False
    assert "Failed to create file" in res_coll.output or "directory" in res_coll.output


@pytest.mark.asyncio
async def test_delete_file_edge_cases(tmp_path: Path) -> None:
    sandbox = PathSandbox(tmp_path)
    tool = DeleteFileTool(sandbox)

    # Missing path
    res_no_path = await tool.run(path="")
    assert res_no_path.ok is False
    assert res_no_path.error_type == ErrorTypeEnum.TOOL_MISUSE

    # Non-existent file
    res_missing = await tool.run(path="not_here.txt")
    assert res_missing.ok is False
    assert "Cannot delete non-existent file" in res_missing.output

    # Directory path
    folder = tmp_path / "sub_folder"
    folder.mkdir()
    res_dir = await tool.run(path="sub_folder")
    assert res_dir.ok is False
    assert "directory" in res_dir.output

    # Traversal attempt
    res_traversal = await tool.run(path="../escape.txt")
    assert res_traversal.ok is False
    assert res_traversal.error_type == ErrorTypeEnum.PERMISSION


# ============================================================================
# LLM Factory Tests
# ============================================================================


def test_llm_factory_creations() -> None:
    # Default provider
    default_p = get_default_provider()
    assert default_p is not None

    # Mock
    mock_p = create_provider(provider_name="mock", model="mock-model")
    assert mock_p.provider_name == "mock"

    # OpenAI
    oa_p = create_provider(provider_name="openai", model="gpt-4o", api_key="sk-test-fake-key")
    assert oa_p.provider_name == "openai"

    # Anthropic
    anth_p = create_provider(
        provider_name="anthropic",
        model="claude-3-5-sonnet",
        api_key="sk-ant-test-fake-key",
    )
    assert anth_p.provider_name == "anthropic"

    # Gemini
    gem_p = create_provider(
        provider_name="gemini", model="gemini-1.5-flash", api_key="AIzaSyTestFakeKey"
    )
    assert gem_p.provider_name == "gemini"

    # DeepSeek
    ds_p = create_provider(
        provider_name="deepseek", model="deepseek-coder", api_key="sk-ds-fake-key"
    )
    assert ds_p.provider_name == "deepseek"

    # Ollama
    ollama_p = create_provider(provider_name="ollama", model="llama3")
    assert ollama_p.provider_name == "ollama"

    # OpenAI Compatible
    oac_p = create_provider(
        provider_name="openai_compatible",
        model="local-model",
        base_url="http://localhost:8000/v1",
        api_key="none",
    )
    assert oac_p.provider_name == "openai_compatible"

    # Unknown provider
    with pytest.raises(LLMError, match="Unknown LLM provider"):
        create_provider(provider_name="unsupported_provider_xyz")
