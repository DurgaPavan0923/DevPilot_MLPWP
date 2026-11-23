"""Custom exception hierarchy for DevPilot."""

from typing import Any


class DevPilotError(Exception):
    """Root exception for all DevPilot runtime errors."""

    def __init__(
        self,
        message: str,
        code: str = "DEVPILOT_ERROR",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details or {}

    def to_dict(self) -> dict[str, Any]:
        return {
            "error": self.__class__.__name__,
            "message": self.message,
            "code": self.code,
            "details": self.details,
        }


# LLM Subsystem Exceptions
class LLMError(DevPilotError):
    """Base exception for LLM provider errors."""

    def __init__(
        self,
        message: str,
        code: str = "LLM_ERROR",
        provider: str | None = None,
        model: str | None = None,
        status_code: int | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        details_dict = details or {}
        if provider:
            details_dict["provider"] = provider
        if model:
            details_dict["model"] = model
        if status_code is not None:
            details_dict["status_code"] = status_code
        super().__init__(message, code=code, details=details_dict)
        self.provider = provider
        self.model = model
        self.status_code = status_code


class LLMAuthenticationError(LLMError):
    """Raised when provider API key or credentials are invalid."""

    def __init__(
        self,
        message: str = "LLM provider authentication failed",
        provider: str | None = None,
        model: str | None = None,
    ) -> None:
        super().__init__(
            message, code="LLM_AUTH_ERROR", provider=provider, model=model, status_code=401
        )


class LLMRateLimitError(LLMError):
    """Raised when provider rate limit is exceeded."""

    def __init__(
        self,
        message: str = "LLM provider rate limit exceeded",
        provider: str | None = None,
        model: str | None = None,
        retry_after: float | None = None,
    ) -> None:
        details = {"retry_after": retry_after} if retry_after else {}
        super().__init__(
            message,
            code="LLM_RATE_LIMIT",
            provider=provider,
            model=model,
            status_code=429,
            details=details,
        )
        self.retry_after = retry_after


class LLMContextLengthExceededError(LLMError):
    """Raised when prompt tokens exceed model context window limit."""

    def __init__(
        self,
        message: str = "Prompt tokens exceed model context window",
        provider: str | None = None,
        model: str | None = None,
        tokens: int | None = None,
        max_tokens: int | None = None,
    ) -> None:
        super().__init__(
            message,
            code="LLM_CONTEXT_EXCEEDED",
            provider=provider,
            model=model,
            status_code=400,
            details={"tokens": tokens, "max_tokens": max_tokens},
        )


class LLMProviderUnavailableError(LLMError):
    """Raised when provider returns 5xx or connection fails."""

    def __init__(
        self,
        message: str = "LLM provider endpoint unreachable or unavailable",
        provider: str | None = None,
        model: str | None = None,
        status_code: int | None = 503,
    ) -> None:
        super().__init__(
            message,
            code="LLM_UNAVAILABLE",
            provider=provider,
            model=model,
            status_code=status_code,
        )


# Tool Subsystem Exceptions
class ToolError(DevPilotError):
    """Base exception for tool execution errors."""

    def __init__(
        self,
        message: str,
        tool_name: str,
        code: str = "TOOL_ERROR",
        details: dict[str, Any] | None = None,
    ) -> None:
        details_dict = details or {}
        details_dict["tool_name"] = tool_name
        super().__init__(message, code=code, details=details_dict)
        self.tool_name = tool_name


class ToolValidationError(ToolError):
    """Raised when tool arguments fail schema validation."""

    def __init__(
        self,
        message: str,
        tool_name: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message, tool_name=tool_name, code="TOOL_VALIDATION_ERROR", details=details
        )


class ToolPermissionDeniedError(ToolError):
    """Raised when tool execution is denied by safety policy or user."""

    def __init__(
        self,
        message: str,
        tool_name: str,
        action: str | None = None,
    ) -> None:
        details = {"action": action} if action else {}
        super().__init__(
            message, tool_name=tool_name, code="TOOL_PERMISSION_DENIED", details=details
        )


class ToolTimeoutError(ToolError):
    """Raised when tool execution exceeds configured timeout limit."""

    def __init__(
        self,
        message: str,
        tool_name: str,
        timeout_seconds: float,
    ) -> None:
        super().__init__(
            message,
            tool_name=tool_name,
            code="TOOL_TIMEOUT",
            details={"timeout_seconds": timeout_seconds},
        )


class ToolExecutionError(ToolError):
    """Raised when tool command or operation fails during execution."""

    def __init__(
        self,
        message: str,
        tool_name: str,
        exit_code: int | None = None,
        stderr: str | None = None,
    ) -> None:
        super().__init__(
            message,
            tool_name=tool_name,
            code="TOOL_EXEC_ERROR",
            details={"exit_code": exit_code, "stderr": stderr},
        )


# Safety & Environment Exceptions
class SafetyError(DevPilotError):
    """Raised on path traversal, dangerous command execution, or policy violation."""

    def __init__(
        self,
        message: str,
        policy: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        details_dict = details or {}
        details_dict["policy"] = policy
        super().__init__(message, code="SAFETY_VIOLATION", details=details_dict)


class RepositoryError(DevPilotError):
    """Raised on repository scanning, git, or tree-sitter failures."""

    def __init__(
        self,
        message: str,
        path: str | None = None,
        code: str = "REPO_ERROR",
    ) -> None:
        super().__init__(message, code=code, details={"path": path} if path else {})


class RecoveryError(DevPilotError):
    """Raised when bounded recovery ladder exhausts all retries or detects loops."""

    def __init__(
        self,
        message: str,
        loop_signature: str | None = None,
        attempt_count: int = 0,
    ) -> None:
        super().__init__(
            message,
            code="RECOVERY_EXHAUSTED",
            details={"loop_signature": loop_signature, "attempt_count": attempt_count},
        )
