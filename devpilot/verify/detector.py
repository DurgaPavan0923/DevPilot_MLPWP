"""Test framework auto-detection."""

from enum import StrEnum
from pathlib import Path


class TestFramework(StrEnum):
    PYTEST = "pytest"
    UNITTEST = "unittest"
    JEST = "jest"
    MOCHA = "mocha"
    MAVEN = "maven"
    GRADLE = "gradle"
    GO_TEST = "go_test"
    UNKNOWN = "unknown"


class TestFrameworkDetector:
    """Detects available test harness in a repository."""

    @staticmethod
    def detect(repo_root: Path) -> TestFramework:
        root = repo_root.resolve()

        if (
            (root / "pytest.ini").exists()
            or (root / "setup.cfg").exists()
            or (root / "tests").exists()
        ):
            return TestFramework.PYTEST
        if (root / "package.json").exists():
            pkg_text = (root / "package.json").read_text(encoding="utf-8", errors="ignore").lower()
            if "jest" in pkg_text:
                return TestFramework.JEST
            if "mocha" in pkg_text:
                return TestFramework.MOCHA
            return TestFramework.JEST
        if (root / "pom.xml").exists():
            return TestFramework.MAVEN
        if (root / "build.gradle").exists() or (root / "build.gradle.kts").exists():
            return TestFramework.GRADLE
        if (root / "go.mod").exists():
            return TestFramework.GO_TEST

        return TestFramework.UNKNOWN
