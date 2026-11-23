"""Base abstract Tool class and output truncation utilities."""

import time
from abc import ABC, abstractmethod
from typing import Any

from devpilot.core.types import ErrorTypeEnum, ToolResult
from devpilot.core.utils import truncate_output
from devpilot.llm.base import ToolDefinition

__all__ = ["Tool", "truncate_output"]


class Tool(ABC):
    """Abstract base class for all callable tools exposed to the agent."""

    name: str
    description: str
    parameters: dict[str, Any]

    def to_tool_definition(self) -> ToolDefinition:
        """Converts tool definition to standard ToolDefinition schema."""
        return ToolDefinition(
            name=self.name,
            description=self.description,
            parameters=self.parameters,
        )

    @abstractmethod
    async def execute(self, **kwargs: Any) -> ToolResult:
        """Executes tool action and returns standardized ToolResult envelope."""
        pass

    async def run(self, **kwargs: Any) -> ToolResult:
        """Wrapper measuring execution duration and handling unexpected exceptions."""
        start_time = time.monotonic()
        try:
            result = await self.execute(**kwargs)
            duration_ms = (time.monotonic() - start_time) * 1000.0
            result.duration_ms = round(duration_ms, 2)
            # Apply output truncation if necessary
            truncated_output, is_truncated = truncate_output(result.output)
            result.output = truncated_output
            result.truncated = result.truncated or is_truncated
            return result
        except Exception as exc:
            duration_ms = (time.monotonic() - start_time) * 1000.0
            return ToolResult(
                ok=False,
                output=f"Error executing tool '{self.name}': {str(exc)}",
                error_type=ErrorTypeEnum.TOOL_MISUSE,
                duration_ms=round(duration_ms, 2),
                metadata={"exception": str(exc)},
            )
