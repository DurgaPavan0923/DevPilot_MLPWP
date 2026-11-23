"""Multi-class error signature classifier."""

import re

from devpilot.core.types import ErrorTypeEnum


class ErrorClassifier:
    """Classifies error messages and tracebacks into structured error taxonomy."""

    SYNTAX_PATTERNS = [
        re.compile(r"SyntaxError", re.IGNORECASE),
        re.compile(r"IndentationError", re.IGNORECASE),
        re.compile(r"unexpected token", re.IGNORECASE),
        re.compile(r"parsing error", re.IGNORECASE),
        re.compile(r"unterminated string", re.IGNORECASE),
    ]

    IMPORT_PATTERNS = [
        re.compile(r"ModuleNotFoundError", re.IGNORECASE),
        re.compile(r"ImportError", re.IGNORECASE),
        re.compile(r"cannot find module", re.IGNORECASE),
        re.compile(r"No module named", re.IGNORECASE),
    ]

    TEST_PATTERNS = [
        re.compile(r"AssertionError", re.IGNORECASE),
        re.compile(r"FAILED\s+\(failures=\d+\)", re.IGNORECASE),
        re.compile(r"=+\s+FAILURES\s+=+", re.IGNORECASE),
        re.compile(r"\bFAIL\b.*\.test\.", re.IGNORECASE),
        re.compile(r"Expected.*Received", re.IGNORECASE),
    ]

    TIMEOUT_PATTERNS = [
        re.compile(r"timed out after", re.IGNORECASE),
        re.compile(r"TimeoutError", re.IGNORECASE),
        re.compile(r"deadline exceeded", re.IGNORECASE),
    ]

    PERMISSION_PATTERNS = [
        re.compile(r"Permission denied", re.IGNORECASE),
        re.compile(r"SafetyError", re.IGNORECASE),
        re.compile(r"blocked by security policy", re.IGNORECASE),
        re.compile(r"Path traversal detected", re.IGNORECASE),
    ]

    TOOL_MISUSE_PATTERNS = [
        re.compile(r"target block was not found", re.IGNORECASE),
        re.compile(r"target block is ambiguous", re.IGNORECASE),
        re.compile(r"File not found", re.IGNORECASE),
        re.compile(r"Tool.*is not recognized", re.IGNORECASE),
        re.compile(r"Must provide", re.IGNORECASE),
    ]

    @classmethod
    def classify(cls, error_text: str, exit_code: int | None = None) -> ErrorTypeEnum:
        """Categorizes raw error text into an ErrorTypeEnum."""
        if not error_text:
            return ErrorTypeEnum.UNKNOWN

        for p in cls.PERMISSION_PATTERNS:
            if p.search(error_text):
                return ErrorTypeEnum.PERMISSION

        for p in cls.TIMEOUT_PATTERNS:
            if p.search(error_text):
                return ErrorTypeEnum.TIMEOUT

        for p in cls.SYNTAX_PATTERNS:
            if p.search(error_text):
                return ErrorTypeEnum.SYNTAX

        for p in cls.IMPORT_PATTERNS:
            if p.search(error_text):
                return ErrorTypeEnum.IMPORT

        for p in cls.TEST_PATTERNS:
            if p.search(error_text):
                return ErrorTypeEnum.TEST_FAILURE

        for p in cls.TOOL_MISUSE_PATTERNS:
            if p.search(error_text):
                return ErrorTypeEnum.TOOL_MISUSE

        if exit_code is not None and exit_code != 0:
            return ErrorTypeEnum.ENVIRONMENT

        return ErrorTypeEnum.UNKNOWN
