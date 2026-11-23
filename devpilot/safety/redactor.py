"""Secret and sensitive token redaction engine for logs, prompts, and tool outputs."""

import re
from re import Pattern
from typing import Any

SECRET_PATTERNS: list[tuple[Pattern[str], str]] = [
    # Anthropic API keys (must be matched before generic sk-)
    (re.compile(r"sk-ant-[a-zA-Z0-9_-]{20,}", re.IGNORECASE), "[REDACTED_ANTHROPIC_KEY]"),
    # OpenAI / DeepSeek API keys
    (re.compile(r"sk-[a-zA-Z0-9_-]{20,}", re.IGNORECASE), "[REDACTED_OPENAI_KEY]"),
    # Google Gemini API keys
    (re.compile(r"AIzaSy[a-zA-Z0-9_-]{30,40}", re.IGNORECASE), "[REDACTED_GEMINI_KEY]"),
    # GitHub Personal Access Tokens
    (re.compile(r"gh[pousr]_[A-Za-z0-9_]{36,}", re.IGNORECASE), "[REDACTED_GITHUB_TOKEN]"),
    # AWS Access Key IDs
    (re.compile(r"\b(AKIA[0-9A-Z]{16})\b"), "[REDACTED_AWS_KEY]"),
    # Slack Tokens
    (re.compile(r"xox[baprs]-[0-9a-zA-Z-]{10,}", re.IGNORECASE), "[REDACTED_SLACK_TOKEN]"),
    # Hugging Face Tokens
    (re.compile(r"hf_[a-zA-Z0-9]{34,}", re.IGNORECASE), "[REDACTED_HF_TOKEN]"),
    # Generic Bearer tokens
    (
        re.compile(r"Bearer\s+[A-Za-z0-9._~+/-]{20,}", re.IGNORECASE),
        "Bearer [REDACTED_BEARER_TOKEN]",
    ),
    # JWT tokens (Header.Payload.Signature)
    (
        re.compile(
            r"eyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}", re.IGNORECASE
        ),
        "[REDACTED_JWT]",
    ),
    # Private Keys (RSA, EC, OPENSSH, PGP)
    (
        re.compile(
            r"-----BEGIN (?:RSA |EC |OPENSSH |PGP )?PRIVATE KEY-----[\s\S]*?-----END (?:RSA |EC |OPENSSH |PGP )?PRIVATE KEY-----"
        ),
        "[REDACTED_PRIVATE_KEY]",
    ),
    # Database connection strings with credentials: postgres://user:pass@host:port/db
    (
        re.compile(
            r"(?i)(postgres|postgresql|mysql|mongodb|redis)://([^:\s]+):([^@\s]+)@([^\s/:]+)"
        ),
        r"\1://\2:[REDACTED_PASSWORD]@\4",
    ),
    # Common password assignments (ignores already redacted tags)
    (
        re.compile(
            r'(?i)(password|secret|api_key|token|access_key|auth_token)\s*[:=]\s*["\'](?!\[REDACTED)([^"\']{6,})["\']'
        ),
        r'\1="[REDACTED_SECRET]"',
    ),
    # Export assignments in shell / .env: export KEY=val
    (
        re.compile(
            r'(?i)^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*(?:SECRET|KEY|TOKEN|PASSWORD|PASS))\s*=\s*(?!["\']?\[REDACTED)(["\']?[^\s"\']{6,}["\']?)',
            re.MULTILINE,
        ),
        r"\1=[REDACTED_SECRET]",
    ),
]


class SecretRedactor:
    """Masks credentials, private keys, and high-entropy authentication tokens."""

    @classmethod
    def redact(cls, text: str) -> str:
        """Sanitizes text by replacing sensitive patterns with masked placeholders."""
        if not text:
            return ""

        sanitized = text
        for pattern, replacement in SECRET_PATTERNS:
            sanitized = pattern.sub(replacement, sanitized)

        return sanitized

    @classmethod
    def redact_data(cls, data: Any) -> Any:
        """Recursively sanitizes dictionary, list, or primitive data structures."""
        if isinstance(data, str):
            return cls.redact(data)
        elif isinstance(data, dict):
            return {k: cls.redact_data(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [cls.redact_data(v) for v in data]
        return data
