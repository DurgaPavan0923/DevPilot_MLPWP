"""DevPilot core foundations: exceptions, types, logging, and base models."""

from devpilot.core.exceptions import (
    DevPilotError,
    LLMAuthenticationError,
    LLMContextLengthExceededError,
    LLMError,
    LLMProviderUnavailableError,
    LLMRateLimitError,
    RecoveryError,
    RepositoryError,
    SafetyError,
    ToolError,
    ToolExecutionError,
    ToolPermissionDeniedError,
    ToolTimeoutError,
    ToolValidationError,
)
from devpilot.core.logging import configure_logging, get_logger

__all__ = [
    "DevPilotError",
    "LLMError",
    "LLMAuthenticationError",
    "LLMRateLimitError",
    "LLMContextLengthExceededError",
    "LLMProviderUnavailableError",
    "ToolError",
    "ToolExecutionError",
    "ToolValidationError",
    "ToolPermissionDeniedError",
    "ToolTimeoutError",
    "SafetyError",
    "RepositoryError",
    "RecoveryError",
    "get_logger",
    "configure_logging",
]
