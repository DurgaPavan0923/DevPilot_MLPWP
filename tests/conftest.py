"""Pytest fixtures for DevPilot test suites."""

import pytest

from devpilot.llm.adapters.mock import MockProvider
from devpilot.llm.base import Message, ToolDefinition


@pytest.fixture
def mock_provider() -> MockProvider:
    """Provides a clean MockProvider instance."""
    return MockProvider(model="mock-agent-model")


@pytest.fixture
def sample_messages() -> list[Message]:
    """Provides standard conversation message history."""
    return [
        Message.system("You are an expert software engineer coding assistant."),
        Message.user("Please fix the bug in server.py"),
    ]


@pytest.fixture
def sample_tools() -> list[ToolDefinition]:
    """Provides sample tool definitions matching the core toolset."""
    return [
        ToolDefinition(
            name="read_file",
            description="Read file contents from the repository",
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Relative file path"},
                    "start_line": {"type": "integer", "description": "Starting line number"},
                    "end_line": {"type": "integer", "description": "Ending line number"},
                },
                "required": ["path"],
            },
        ),
        ToolDefinition(
            name="edit_file",
            description="Apply changes to a file using exact search and replace",
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "target": {"type": "string"},
                    "replacement": {"type": "string"},
                },
                "required": ["path", "target", "replacement"],
            },
        ),
    ]
