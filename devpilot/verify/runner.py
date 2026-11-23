"""Verification runner: executes targeted test suites and generates audit reports."""

import asyncio
import os
import re
import sys
import time
from pathlib import Path

from pydantic import BaseModel, Field

from devpilot.verify.detector import TestFramework, TestFrameworkDetector


class VerificationReport(BaseModel):
    status: str = "VERIFIED"  # "VERIFIED", "FAILED", "UNVERIFIED"
    passed: bool
    framework: str
    total_tests: int = 0
    passed_tests: int = 0
    failed_tests: int = 0
    duration_ms: float = 0.0
    stdout: str = ""
    modified_files: list[str] = Field(default_factory=list)
    git_diff: str | None = None


class VerificationRunner:
    """Orchestrates test verification passes and produces structured reports."""

    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root.resolve()
        self.framework = TestFrameworkDetector.detect(self.repo_root)

    def _get_test_argv(self, target: str | None = None) -> list[str]:
        if self.framework == TestFramework.PYTEST:
            argv = [sys.executable, "-m", "pytest"]
            if target:
                argv.append(target)
            return argv
        elif self.framework in (TestFramework.JEST, TestFramework.MOCHA):
            argv = ["npm", "test", "--"]
            if target:
                argv.append(target)
            return argv
        elif self.framework == TestFramework.MAVEN:
            return ["mvn", "test"]
        elif self.framework == TestFramework.GRADLE:
            return ["./gradlew" if os.name != "nt" else "gradlew.bat", "test"]
        elif self.framework == TestFramework.GO_TEST:
            return ["go", "test", target or "./..."]
        elif self.framework == TestFramework.UNITTEST:
            argv = [sys.executable, "-m", "unittest"]
            if target:
                argv.append(target)
            return argv
        return []

    async def run_verification(
        self,
        target_test: str | None = None,
        modified_files: list[str] | None = None,
        timeout_sec: float = 120.0,
    ) -> VerificationReport:
        if self.framework == TestFramework.UNKNOWN:
            return VerificationReport(
                status="UNVERIFIED",
                passed=False,
                framework=self.framework.value,
                duration_ms=0.0,
                stdout="No test framework detected in repository. Status is UNVERIFIED.",
                modified_files=modified_files or [],
            )

        argv = self._get_test_argv(target_test)
        if not argv:
            return VerificationReport(
                status="UNVERIFIED",
                passed=False,
                framework=self.framework.value,
                duration_ms=0.0,
                stdout="Unable to construct test command for detected framework.",
                modified_files=modified_files or [],
            )

        start_time = time.monotonic()
        env = {**os.environ, "PYTHONPATH": str(self.repo_root)}

        try:
            # create_subprocess_exec directly passes argv without shell interpretation
            process = await asyncio.create_subprocess_exec(
                argv[0],
                *argv[1:],
                cwd=str(self.repo_root),
                env=env,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                process.communicate(), timeout=timeout_sec
            )
            elapsed_ms = (time.monotonic() - start_time) * 1000.0

            out_text = stdout_bytes.decode("utf-8", errors="replace")
            err_text = stderr_bytes.decode("utf-8", errors="replace")
            combined = f"{out_text}\n{err_text}".strip()

            passed = process.returncode == 0

            # Heuristic test counting
            passed_count = len(re.findall(r"\bPASSED\b", combined))
            failed_count = len(re.findall(r"\bFAILED\b", combined))

            return VerificationReport(
                status="VERIFIED" if passed else "FAILED",
                passed=passed,
                framework=self.framework.value,
                total_tests=passed_count + failed_count,
                passed_tests=passed_count,
                failed_tests=failed_count,
                duration_ms=round(elapsed_ms, 2),
                stdout=combined[:5000],
                modified_files=modified_files or [],
            )
        except Exception as exc:
            elapsed_ms = (time.monotonic() - start_time) * 1000.0
            return VerificationReport(
                status="FAILED",
                passed=False,
                framework=self.framework.value,
                duration_ms=round(elapsed_ms, 2),
                stdout=f"Verification execution failure: {str(exc)}",
                modified_files=modified_files or [],
            )
