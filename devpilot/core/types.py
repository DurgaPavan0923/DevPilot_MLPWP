"""Core type definitions, enums, and universal models for DevPilot."""

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class PermissionMode(StrEnum):
    """Safety permission modes governing tool executions."""

    READ_ONLY = "read-only"
    ASK = "ask"
    AUTO_SAFE = "auto-safe"
    FULL = "full"


class AgentStateEnum(StrEnum):
    """Finite State Machine states of the agent runtime."""

    INIT = "INIT"
    ANALYZE = "ANALYZE"
    RETRIEVE = "RETRIEVE"
    PLAN = "PLAN"
    ACT = "ACT"
    OBSERVE = "OBSERVE"
    RECOVER = "RECOVER"
    VERIFY = "VERIFY"
    DONE = "DONE"
    FAILED = "FAILED"


class ErrorTypeEnum(StrEnum):
    """Categorized error signatures for structured feedback and recovery."""

    SYNTAX = "syntax"
    IMPORT = "import"
    TEST_FAILURE = "test-failure"
    TIMEOUT = "timeout"
    PERMISSION = "permission"
    TOOL_MISUSE = "tool-misuse"
    ENVIRONMENT = "environment"
    UNKNOWN = "unknown"


class AgentConfigPreset(StrEnum):
    """Evaluation harness agent configurations."""

    BASIC = "basic"
    FIXED_RAG = "fixed_rag"
    FULL = "full"


class ToolResult(BaseModel):
    """Uniform structured envelope returned by all DevPilot tool executions."""

    ok: bool = Field(..., description="True if operation succeeded, False otherwise")
    output: str = Field(..., description="Execution stdout, file content, or success payload")
    error_type: ErrorTypeEnum | None = Field(
        None, description="Classified error type if ok is False"
    )
    exit_code: int | None = Field(None, description="Process return code if command execution")
    duration_ms: float = Field(0.0, description="Execution elapsed time in milliseconds")
    truncated: bool = Field(False, description="True if output was trimmed by size limits")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Supplementary tool data")
