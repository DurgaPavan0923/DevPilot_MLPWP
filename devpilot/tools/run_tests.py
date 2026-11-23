"""Tool: run_tests with framework auto-detection and Docker/subprocess execution."""

import os
import sys
from typing import Any

from devpilot.core.types import ErrorTypeEnum, ToolResult
from devpilot.safety.docker_executor import DockerExecutor
from devpilot.safety.sandbox import PathSandbox
from devpilot.tools.base import Tool


class RunTestsTool(Tool):
    name = "run_tests"
    description = (
        "Execute repository test suite with framework auto-detection (pytest, npm test, etc.)."
    )
    parameters = {
        "type": "object",
        "properties": {
            "test_target": {
                "type": "string",
                "description": "Specific test file or test function path",
            },
            "framework": {
                "type": "string",
                "description": "Explicit framework override (pytest, npm, etc.)",
            },
        },
    }

    def __init__(
        self,
        sandbox: PathSandbox,
        default_timeout_sec: float = 120.0,
        docker_executor: DockerExecutor | None = None,
    ) -> None:
        self.sandbox = sandbox
        self.default_timeout_sec = default_timeout_sec
        self.docker_executor = docker_executor or DockerExecutor(
            repo_root=self.sandbox.repo_root,
            timeout_sec=default_timeout_sec,
            sandbox_enabled=True,
            allow_host_fallback=True,
        )

    def _detect_test_command(self, test_target: str | None, framework: str | None) -> str:
        py_exe = f'"{sys.executable}"'
        if framework:
            if framework == "pytest":
                return f"{py_exe} -m pytest {test_target or ''}".strip()
            elif framework == "npm":
                return f"npm test -- {test_target or ''}".strip()

        # Detection heuristics
        root = self.sandbox.repo_root
        if (
            (root / "pytest.ini").exists()
            or (root / "pyproject.toml").exists()
            or (root / "tests").exists()
        ):
            return f"{py_exe} -m pytest {test_target or ''}".strip()
        if (root / "package.json").exists():
            return f"npm test -- {test_target or ''}".strip()
        if (root / "pom.xml").exists():
            return "mvn test"
        if (root / "go.mod").exists():
            return f"go test {test_target or './...'}"

        return f"{py_exe} -m pytest {test_target or ''}".strip()

    async def execute(
        self, test_target: str | None = None, framework: str | None = None, **kwargs: Any
    ) -> ToolResult:
        cmd = self._detect_test_command(test_target, framework)
        sub_env = dict(os.environ)
        sub_env["PYTHONPATH"] = (
            f"{str(self.sandbox.repo_root)}{os.pathsep}{sub_env.get('PYTHONPATH', '')}"
        )

        res = await self.docker_executor.execute(
            cmd, env=sub_env, timeout_sec=self.default_timeout_sec
        )

        error_type = None
        if not res.ok:
            error_type = (
                ErrorTypeEnum.TIMEOUT
                if res.error_type == ErrorTypeEnum.TIMEOUT
                else ErrorTypeEnum.TEST_FAILURE
            )

        output_text = res.output if res.output else "(No test output produced)"

        return ToolResult(
            ok=res.ok,
            output=output_text,
            exit_code=res.exit_code,
            duration_ms=res.duration_ms,
            error_type=error_type,
            truncated=res.truncated,
            metadata={**res.metadata, "command": cmd, "test_target": test_target},
        )
