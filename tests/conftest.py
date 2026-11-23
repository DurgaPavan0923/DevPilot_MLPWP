"""Pytest fixtures for DevPilot test suites."""

import pytest

import devpilot.context.dense
from devpilot.llm.adapters.mock import MockProvider
from devpilot.llm.base import Message, ToolDefinition


@pytest.fixture(autouse=True)
def disable_neural_dense_by_default(
    request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Disable neural sentence-transformers by default to avoid downloading models in CI.

    Tests marked with @pytest.mark.neural retain the neural backend setting.
    """
    if "neural" not in request.keywords:
        monkeypatch.setattr(devpilot.context.dense, "_HAS_SENTENCE_TRANSFORMERS", False)


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
